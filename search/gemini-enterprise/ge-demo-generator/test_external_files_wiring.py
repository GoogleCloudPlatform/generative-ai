#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Gates where the demo's sample documents end up, and how that is reported (v2.13.0).

There is exactly ONE route into a Google Drive: the deploy-time upload, which
since v2.13.0 calls Drive v3 with this machine's own `gcloud` token, so the
folder is owned by the account deploying the demo. A deployment cannot write
into someone else's Drive, and since v2.11.0 the agent no longer tries either -
the in-chat import is gone. That makes the deploy the only place the documents
can land and the completion banner the only place the user is told what
happened.

So this gate holds four facts, in three files:

  1. the documents are staged to gs://$GCS_BUCKET_NAME/ in EVERY mode - until
     v2.9.0 the copy sat inside the `RAG_MODE` branch, so a demo in mcp mode had
     no bucket at all, and that bucket is now the only copy that outlives the
     operator's machine;
  2. the upload runs against the REST API with a gcloud token and no external
     CLI. Two things are gated here: no `gdrive` binary comes back (it is a
     Google-internal tool, and its path leaked into the published copy of this
     skill), and the one thing that route really can fail on - the token
     carrying no Drive scope - is reported with the re-login that fixes it;
  3. every destination is reported as a link a reader can click - a bare gs://
     URI is not one, and neither is a folder name - and when there is NO Drive
     copy the banner says so, with the reason and with what to do about it;
  4. the in-chat import stays deleted. It uploaded whatever sat at the bucket
     root, which in rag mode is the customer's indexed corpus rather than the
     four generated samples, into an end user's personal Drive without being
     asked. Nothing may quietly reintroduce it - not the tool, not the
     unprompted callback, not the Firestore claim, not DRIVE_FOLDER_URL.

Fact 1 is exercised, not pattern-matched: the job block is sliced out of the
script and run under bash with a stubbed gcloud, once per mode.

    python3 tools/test_external_files_wiring.py
"""
import ast
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP = os.path.join(REPO, "skills/ge-demo-generator/templates/setup_and_deploy.sh")
TOOLS = os.path.join(REPO, "skills/ge-demo-generator/templates/tools.py")
AGENT = os.path.join(REPO, "skills/ge-demo-generator/templates/agent.py")
GEN = os.path.join(REPO, "skills/ge-demo-generator/templates/scripts/"
                         "generate_and_upload_external_files.py")

# The one command that turns a scope-less token into a working Drive upload.
# Both the script and the deploy banner have to print it verbatim, because
# "authorize Drive" sends people to the Cloud console, where it is not.
REAUTH_HINT = "gcloud auth login --enable-gdrive-access --no-launch-browser"

# Every name the deleted feature was made of. None of them may come back.
RETIRED = [
    "import_demo_files_to_my_drive",
    "maybe_auto_import_demo_files",
    "_drive_import_once",
    "_drive_import_run",
    "_drive_import_thread",
    "AUTO_IMPORT_DEMO_FILES",
    "AUTO_IMPORT_WAIT_S",
    "_drive_imports",
]

# gcloud and python3 never run for real here; every invocation is one log line.
PRELUDE = """
# Upper case on purpose: nothing here runs for real, and a lowercase
# project-id-shaped literal reads as a real project to a secret scanner.
PROJECT_ID=STUB_PROJECT_ID
REGION=asia-northeast1
SELECTED_APP_ID=stub-app
SELECTED_LOC=global
TOKEN=stub-token
SERVICE_NAME=stub-svc
DATASET_ID=stub_ds
# Logged to a file, not stdout: the script sends most of these to /dev/null.
gcloud() { echo "gcloud $*" >> "$CALL_LOG"; }
python3() { echo "python3 $*" >> "$CALL_LOG"; }
"""

# name, RAG_MODE, GCS_BUCKET_NAME, must appear, must NOT appear
CASES = [
    ("mcp mode stages the documents", "0", "demo-docs",
     ["buckets create gs://demo-docs", "storage cp -r external_files/"], ["setup_datastores.py"]),
    ("rag mode stages them and indexes", "1", "demo-docs",
     ["buckets create gs://demo-docs", "storage cp -r external_files/", "setup_datastores.py"], []),
    ("no bucket name, nothing staged", "0", "",
     [], ["buckets create", "storage cp"]),
]


def slice_job(src):
    """The Job 3.2b subshell, from its banner to the line that backgrounds it."""
    start = src.index("# Job 3.2b:")
    end = src.index("\n) &\n", start) + len("\n) &\n")
    return src[start:end]


def run_case(job, rag_mode, bucket):
    """Run the job in a throwaway tree that has the files it looks for."""
    with tempfile.TemporaryDirectory() as _dir:
        os.mkdir(os.path.join(_dir, "external_files"))
        open(os.path.join(_dir, "external_files", "audit.pdf"), "w").close()
        os.mkdir(os.path.join(_dir, "scripts"))
        open(os.path.join(_dir, "scripts", "setup_datastores.py"), "w").close()
        log = os.path.join(_dir, "calls.log")
        script = "CALL_LOG=%s\nRAG_MODE=%s\nGCS_BUCKET_NAME=%s\n%s\n%s\nwait\n" % (
            log, rag_mode, bucket, PRELUDE, job)
        subprocess.run(["bash", "-e"], input=script, text=True,
                       capture_output=True, check=False, cwd=_dir)
        return open(log, encoding="utf-8").read() if os.path.exists(log) else ""


def check(cond, label, detail=""):
    print("  %-4s %-52s %s" % ("ok" if cond else "FAIL", label, detail))
    return 0 if cond else 1


def banner_branch(src):
    """The `no Drive copy` arm of the completion banner."""
    marker = 'elif [ ! -z "$DRIVE_SKIP_REASON" ]; then'
    if marker not in src:
        return ""
    start = src.index(marker)
    return src[start:src.index("\nfi\n", start)]


def main():
    failures = 0
    setup_src = open(SETUP, encoding="utf-8").read()
    tools_src = open(TOOLS, encoding="utf-8").read()
    agent_src = open(AGENT, encoding="utf-8").read()
    gen_src = open(GEN, encoding="utf-8").read()
    job = slice_job(setup_src)

    print("1. the sample documents are staged to GCS in every mode")
    for name, rag_mode, bucket, expected, forbidden in CASES:
        log = run_case(job, rag_mode, bucket)
        missing = [e for e in expected if e not in log]
        leaked = [f for f in forbidden if f in log]
        failures += check(not missing and not leaked, name,
                          ("missing %s " % missing if missing else "")
                          + ("unexpected %s" % leaked if leaked else ""))
    failures += check(
        re.search(r'^CR_ENV_VARS="\$\{CR_ENV_VARS\},GCS_BUCKET_NAME=\$\{GCS_BUCKET_NAME\}"$',
                  setup_src, re.M) is not None,
        "the bucket name reaches the container",
        "so the deployed service still records where they are")

    print("\n2. the upload is Drive v3 + a gcloud token, with no external CLI")
    failures += check("https://www.googleapis.com/drive/v3" in gen_src
                      and "gcloud auth print-access-token" in gen_src,
                      "the folder is created with the deploy account's own token",
                      "so it owns the folder and needs no share")
    for name, src in (("the upload script", gen_src), ("setup_and_deploy.sh", setup_src)):
        failures += check(
            "/google/bin/" not in src
            and not re.search(r"gdrive (mutate|readonly|--version)", src)
            and not re.search(r"gdrive_bin|gdrive CLI", src),
            "no gdrive CLI in %s" % name,
            "it is Google-internal; its path leaked into the public copy")
    failures += check(REAUTH_HINT in gen_src,
                      "a token with no Drive scope names the re-login that fixes it",
                      "a plain `gcloud auth login` does not grant it")
    failures += check("share_error" in gen_src and '"share_error": share_error' in gen_src,
                      "a refused link-share is recorded, not swallowed",
                      "'anyone with the link' is often blocked by policy")
    failures += check("SKIP_DRIVE_UPLOAD" in gen_src,
                      "SKIP_DRIVE_UPLOAD opts back out of the upload")
    failures += check("upload_skipped_reason" in gen_src,
                      "a skipped upload carries its reason into the summary")

    print("\n3. every destination is reported, and a missing Drive copy is announced")
    failures += check("https://storage.cloud.google.com/${GCS_BUCKET_NAME}/" in setup_src,
                      "each staged file gets an openable https link",
                      "gs:// is not something anyone can click")
    failures += check(
        "https://console.cloud.google.com/storage/browser/${GCS_BUCKET_NAME}" in setup_src,
        "and the bucket itself opens in the console")
    quick = setup_src.split("Quick Access Links")[-1] if "Quick Access Links" in setup_src else ""
    failures += check("${DRIVE_FOLDER_URL}" in quick and "${GCS_CONSOLE_URL}" in quick,
                      "both show up in the Quick Access Links block")
    failures += check("${DRIVE_OWNER_ACCOUNT}" in setup_src
                      and "LINK SHARING OFF" in setup_src,
                      "the banner names the owner, and a refused link-share")
    skip_branch = banner_branch(setup_src)
    failures += check("${DRIVE_SKIP_REASON}" in skip_branch,
                      "no Drive copy: the banner prints the reason",
                      "this is the only notice the user gets")
    failures += check(REAUTH_HINT in skip_branch and "external_files/" in skip_branch,
                      "and says how to get one",
                      "re-login with the Drive scope, or upload by hand")

    print("\n4. the in-chat import stays deleted")
    for name in RETIRED:
        failures += check(
            name not in tools_src and name not in agent_src and name not in setup_src,
            "no %s" % name)
    # DRIVE_FOLDER_URL survives as a shell variable - the banner parses the
    # summary into it - but it must not reach the container anymore.
    failures += check(",DRIVE_FOLDER_URL=" not in setup_src
                      and "DRIVE_FOLDER_URL" not in tools_src
                      and "DRIVE_FOLDER_URL" not in agent_src,
                      "DRIVE_FOLDER_URL is not passed to Cloud Run",
                      "nothing in the runtime reads it")
    tree = ast.parse(tools_src)
    gate = None
    for node in tree.body:
        if isinstance(node, ast.If) and "ENABLE_WORKSPACE_MCP" in ast.dump(node.test) \
                and any(isinstance(n, ast.FunctionDef) and n.name == "_ma_drive_multipart"
                        for n in node.body):
            gate = node
    # The uploader helpers outlived the import: save_deliverables_to_drive is
    # nested under this same gate and still needs them.
    failures += check(gate is not None,
                      "the Drive uploader helpers stay under the Workspace gate",
                      "save_deliverables_to_drive is their remaining consumer")
    callback = next((n for n in ast.walk(ast.parse(agent_src))
                     if isinstance(n, ast.FunctionDef)
                     and n.name == "_inject_completed_tasks"), None)
    failures += check(callback is not None and "drive" not in ast.unparse(callback).lower(),
                      "the before-agent callback does no Drive work",
                      "it runs on every turn, in front of the user's reply")
    failures += check("cloud storage" in agent_src.lower()
                      and "do NOT offer to copy them into the user's" in agent_src,
                      "the agent is told to say so instead of offering a copy")

    print("\n5. cross-file ID alignment and prompt-to-file binding repair")
    code_gs_path = os.path.join(REPO, "Code.gs")
    if not os.path.isfile(code_gs_path):
        code_gs_path = os.path.join(REPO, "app", "Code.gs")
    index_html_path = os.path.join(REPO, "index.html")
    if not os.path.isfile(index_html_path):
        index_html_path = os.path.join(REPO, "app", "index.html")
    code_gs = open(code_gs_path, encoding="utf-8").read()
    index_html = open(index_html_path, encoding="utf-8").read()
    disc_block = gen_src[gen_src.index("discrepancy_info ="):gen_src.index("generate_pdf(pdf_path")]
    pdf_refs = set(re.findall(r"REF-\d{4}", disc_block))
    excel_refs = {f"REF-{100 + i:04d}" for i in range(1, 51)}
    failures += check(bool(pdf_refs) and pdf_refs.issubset(excel_refs),
                      "fallback PDF discrepancy IDs exist in fallback Excel rows",
                      f"pdf={sorted(pdf_refs)}")
    failures += check(gen_src.count('"is_discrepancy": True') >= 2,
                      "both fallback scanned images include a discrepancy row",
                      "so either scan works for the Vision Showcase prompt")
    failures += check("function validateAndRepairExternalFileBindings_(planResult)" in code_gs
                      and code_gs.count("validateAndRepairExternalFileBindings_(") >= 3,
                      "Code.gs defines and calls validateAndRepairExternalFileBindings_",
                      "wired in planAndGenerateData and validateGeneratedData")
    failures += check(
        code_gs.index("validateAndRepairExternalFileBindings_(parsed)")
        < code_gs.index("[ImageGen-Pipeline] Scanning externalFiles for dynamic images"),
        "repair runs BEFORE ImageGen-Pipeline renders imageRows into pixels")
    failures += check("function resolveStepExternalFiles(step, stepIdx, extFilesArr)" in index_html
                      and index_html.count("resolveStepExternalFiles(") >= 3
                      and "Attach to this prompt in chat:" in index_html,
                      "index.html shares resolveStepExternalFiles across UI and copy")

    # Execute validateAndRepairExternalFileBindings_ (Code.gs) and resolveStepExternalFiles (index.html)
    # in Node to verify runtime behavior on fresh generation, legacy restore, and custom/reordered files.
    import glob
    import shutil
    node_bin = shutil.which("node")
    if not node_bin:
        nvm_nodes = sorted(glob.glob(os.path.expanduser("~/.nvm/versions/node/*/bin/node")))
        if nvm_nodes:
            node_bin = nvm_nodes[-1]
    if node_bin:
        node_test = r"""
const fs = require('fs');
const vm = require('vm');
const codeGs = fs.readFileSync(process.env.CODE_GS_PATH, 'utf8');
const indexHtml = fs.readFileSync(process.env.INDEX_HTML_PATH, 'utf8');

const parseCsvSrc = codeGs.slice(
  codeGs.indexOf('function parseCSVLine('),
  codeGs.indexOf('function repairTruncatedJson(')
);
const repairSrc = codeGs.slice(
  codeGs.indexOf('function validateAndRepairExternalFileBindings_('),
  codeGs.indexOf('function validateGeneratedData(')
);
const resolveSrc = indexHtml.slice(
  indexHtml.indexOf('function resolveStepExternalFiles('),
  indexHtml.indexOf('function copyAllDemoGuide(')
);

const ctx = { console: { log: () => {}, warn: () => {} } };
vm.createContext(ctx);
vm.runInContext(parseCsvSrc, ctx);
vm.runInContext(repairSrc, ctx);
vm.runInContext(resolveSrc, ctx);

// Case A: Fresh generation (Call 1 pre-ImageGen -> ImageGen sets base64Data -> Call 2 post-ImageGen)
const freshPlan = {
  tables: [
    {
      tableName: 'custom_mold_configurations',
      csvData: [
        'config_id,order_id,customer_name,total_weight_kg,config_Timestamp',
        'CFG-2026-8801,ORD-2026-5501,Alpha Tooling GmbH,410.0,2026-09-10 08:00:00',
        'CFG-2026-8802,ORD-2026-5502,Bavaria Precision GmbH,380.0,2026-06-25 14:30:00',
        'CFG-2026-8841,ORD-2026-5541,Alpine Mold OG,395.0,2026-09-21 09:30:00'
      ].join('\n')
    },
    {
      tableName: 'mold_components_catalog',
      csvData: [
        'component_id,component_name,lifecycle_status',
        'K20-296-296-36,Clamping Plate,ACTIVE',
        'K500-ALT,Legacy Clamping Plate,OBSOLETE'
      ].join('\n')
    }
  ],
  externalFiles: [
    {
      id: 'file1',
      fileName: 'quarterly_mold_procurement_audit.pdf',
      mimeType: 'application/pdf',
      fileContent: 'Audit flagged CFG-2026-8802, CFG-2026-8812, and CFG-2026-8841 for surcharge cap review.'
    },
    {
      id: 'file2',
      fileName: 'handwritten_mold_order_task1.jpg',
      mimeType: 'image/jpeg',
      description: 'Scanned handwritten mold order sheet with normal quantities',
      imageColumns: ['Pos.', 'Code / Dim', 'Qty', 'Description'],
      imageRows: [
        '1 | K20 / 296x296x36 | 2 | Clamping Plate',
        '2 | K30 / 296x296x56 | 2 | Cavity Plate',
        '3 | Z01 / 24x120 | 4 | Leader Pin'
      ]
    },
    {
      id: 'file3',
      fileName: 'handwritten_mold_order_task2.jpg',
      mimeType: 'image/jpeg',
      description: 'Scanned order sheet with obsolete code',
      imageColumns: ['Pos.', 'Code / Dim', 'Qty', 'Description'],
      imageRows: [
        '1 | K500-ALT / 246 296 / 36 | 2 | Legacy Clamping Plate (Obsolete code - check replacement)'
      ]
    },
    {
      id: 'file4',
      fileName: 'supplier_steel_alloy_surcharge_feed.xlsx',
      mimeType: 'text/tab-separated-values',
      fileContent: [
        'log_id\tsteel_grade\tsupplier_id\tconfig_id\tsurcharge_variance_pct\tshipment_weight_kg\tinvoice_date\taudit_flag',
        'LOG-STL-101\t1.2312\tSUP-DE\tCFG-2026-8801\t2.4%\t410 kg\t2026-09-01\tPASS',
        'LOG-STL-102\t1.2343 ESR\tSUP-AT\tCFG-2026-8802\t31.3%\t380 kg\t2026-09-02\tDISCREPANCY_EXCEEDS_CAP'
      ].join('\n')
    }
  ],
  demoGuide: [
    { title: 'Baseline Overview', prompt: 'Show revenue.', requiredFileId: '' },
    { title: 'Drill Down', prompt: 'Filter by grade.', requiredFileId: 'none' },
    {
      title: 'Cross-Source Audit & Supplier Feed',
      prompt: 'Cross-reference quarterly_mold_procurement_audit.pdf with supplier_steel_alloy_surcharge_feed.xlsx.',
      watchPoint: 'Flags CFG-2026-8802, CFG-2026-8812, and CFG-2026-8899.',
      requiredFileId: 'file1'
    },
    {
      title: 'Handwritten Order Sheet Vision Showcase',
      prompt: 'Extract all line items from this handwritten mold order sheet and flag any obsolete code.',
      requiredFileId: 'file2'
    },
    { title: 'Executive Summary', prompt: 'Summarize.', requiredFileId: '' },
    { title: 'Action', prompt: 'Create ticket.', requiredFileId: '' },
    {
      title: 'Live Market Benchmark & Board Deck',
      prompt: 'Browse tradingeconomics.com online and create a presentation deck.',
      requiredFileId: 'file1'
    }
  ]
};

// Call 1 (before ImageGen renders base64Data)
ctx.validateAndRepairExternalFileBindings_(freshPlan);
// Simulate ImageGen rendering base64Data from the repaired imageRows
freshPlan.externalFiles[1].base64Data = 'RENDERED_B64_1';
freshPlan.externalFiles[2].base64Data = 'RENDERED_B64_2';
// Call 2 (inside validateGeneratedData after ImageGen)
ctx.validateAndRepairExternalFileBindings_(freshPlan);

if (freshPlan.externalFiles[0].fileContent.includes('CFG-2026-8812')) throw new Error('Hallucinated PDF ID not repaired');
if (!freshPlan.externalFiles[0].fileContent.includes('CFG-2026-8801')) throw new Error('Missing replacement ID CFG-2026-8801');
if (freshPlan.demoGuide[2].watchPoint.includes('CFG-2026-8812') || freshPlan.demoGuide[2].watchPoint.includes('CFG-2026-8899')) {
  throw new Error('Hallucinated watchPoint IDs not repaired: ' + freshPlan.demoGuide[2].watchPoint);
}
if (!freshPlan.externalFiles[3].fileContent.includes('LOG-STL-103\t1.2343 ESR\tSUP-AT\tCFG-2026-8841\t31.3%\t395 kg\t2026-09-21\tDISCREPANCY_EXCEEDS_CAP')) {
  throw new Error('Appended Excel row did not increment PK or sync weight/date: ' + freshPlan.externalFiles[3].fileContent);
}
if (!freshPlan.externalFiles[1].imageRows[3].startsWith('4 | K500-ALT')) {
  throw new Error('Injected imageRows item was not renumbered to Pos 4: ' + freshPlan.externalFiles[1].imageRows[3]);
}
if (freshPlan.demoGuide[2].requiredFileId !== 'file1,file4') {
  throw new Error('Expected Prompt 3 requiredFileId=file1,file4, got ' + freshPlan.demoGuide[2].requiredFileId);
}
if (freshPlan.demoGuide[3].requiredFileId !== 'file2') {
  throw new Error('Expected fresh Prompt 4 requiredFileId=file2, got ' + freshPlan.demoGuide[3].requiredFileId);
}
if (freshPlan.demoGuide[6].requiredFileId !== '') {
  throw new Error('Expected Prompt 7 duplicate file1 cleared, got ' + freshPlan.demoGuide[6].requiredFileId);
}

// Case B: Legacy backup restore with dataPreview only + pre-rendered base64Data
const legacyRestore = {
  tables: [],
  dataPreview: [
    {
      tableName: 'custom_mold_configurations',
      headers: ['config_id', 'customer_name'],
      rows: [['CFG-2026-8801', 'Alpha'], ['CFG-2026-8802', 'Bavaria']]
    }
  ],
  externalFiles: [
    { id: 'file1', fileName: 'audit.pdf', mimeType: 'application/pdf', fileContent: 'Check CFG-2026-8899.' },
    { id: 'file2', fileName: 'scan1.jpg', mimeType: 'image/jpeg', base64Data: 'RENDERED', imageRows: ['1 | K20 | 2 | Normal'] },
    { id: 'file3', fileName: 'scan2.jpg', mimeType: 'image/jpeg', base64Data: 'RENDERED', imageRows: ['1 | K500-ALT | 1 | Obsolete code'] }
  ],
  demoGuide: [
    { title: 'S1', prompt: 'Q1', requiredFileId: '' },
    { title: 'S2', prompt: 'Q2', requiredFileId: '' },
    { title: 'S3', prompt: 'Check audit.pdf', requiredFileId: 'file1' },
    { title: 'Vision Showcase', prompt: 'Extract from handwritten order sheet', requiredFileId: 'file2' }
  ]
};
ctx.validateAndRepairExternalFileBindings_(legacyRestore);
if (!legacyRestore.externalFiles[0].fileContent.includes('CFG-2026-8801')) {
  throw new Error('dataPreview indexing failed to repair PDF ID');
}
if (legacyRestore.demoGuide[3].requiredFileId !== 'file2,file3') {
  throw new Error('Legacy pre-rendered image should bind file2,file3, got ' + legacyRestore.demoGuide[3].requiredFileId);
}

// Case C: Non-standard externalFiles ordering [pdf, xlsx, img1, img2] with custom IDs
const reordered = {
  tables: [],
  externalFiles: [
    { id: 'pdf_doc', fileName: 'audit_report.pdf', mimeType: 'application/pdf', fileContent: 'Audit' },
    { id: 'xlsx_doc', fileName: 'supplier_surcharge_feed.xlsx', mimeType: 'text/tab-separated-values', fileContent: 'a\tb\n1\t2' },
    { id: 'scan_1', fileName: 'order_scan_1.jpg', mimeType: 'image/jpeg', imageRows: ['1 | X-999 | 1 | Obsolete code'] },
    { id: 'scan_2', fileName: 'order_scan_2.jpg', mimeType: 'image/jpeg', imageRows: ['1 | Y-999 | 1 | Obsolete code'] }
  ],
  demoGuide: [
    { title: 'S1', prompt: 'Q1', requiredFileId: '' },
    { title: 'S2', prompt: 'Q2', requiredFileId: '' },
    { title: 'Cross-Source', prompt: 'Cross-reference audit report with supplier surcharge feed.', requiredFileId: 'file1,file4' },
    { title: 'Vision OCR', prompt: 'Extract items from handwritten order sheet.', requiredFileId: 'file2' }
  ]
};
ctx.validateAndRepairExternalFileBindings_(reordered);
if (reordered.demoGuide[2].requiredFileId !== 'pdf_doc,xlsx_doc') {
  throw new Error('Reordered Cross-Source binding failed: ' + reordered.demoGuide[2].requiredFileId);
}
if (reordered.demoGuide[3].requiredFileId !== 'scan_1') {
  throw new Error('Reordered Vision binding failed: ' + reordered.demoGuide[3].requiredFileId);
}
const uiBound = ctx.resolveStepExternalFiles(reordered.demoGuide[2], 2, reordered.externalFiles);
if (uiBound.length !== 2 || uiBound[0].file.id !== 'pdf_doc' || uiBound[1].file.id !== 'xlsx_doc') {
  throw new Error('resolveStepExternalFiles failed on custom IDs');
}
console.log('ALL_NODE_TESTS_OK');
"""
        node_env = {**os.environ, "CODE_GS_PATH": code_gs_path, "INDEX_HTML_PATH": index_html_path}
        proc = subprocess.run([node_bin, "-e", node_test], cwd=REPO, env=node_env, text=True, capture_output=True, check=False)
        failures += check(proc.returncode == 0 and "ALL_NODE_TESTS_OK" in proc.stdout,
                          "runtime repair executes cleanly on fresh, legacy, and reordered specs",
                          (proc.stderr or proc.stdout).strip()[:200] if proc.returncode != 0 else "")

    # Exercise verify_and_heal.py's check_external_files_consistency on a synthetic spec
    import csv as _csv
    import glob as _glob
    import json as _json
    vh_path = os.path.join(REPO, "skills/ge-demo-generator/templates/scripts/verify_and_heal.py")
    vh_src = open(vh_path, encoding="utf-8").read()
    vh_lines = vh_src.splitlines()
    vh_tree = ast.parse(vh_src)
    fn_node = next(n for n in vh_tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "check_external_files_consistency")
    fn_code = "\n".join(vh_lines[fn_node.lineno - 1:fn_node.end_lineno])
    vh_ns = {"os": os, "re": re, "csv": _csv, "glob": _glob, "json": _json}
    exec(fn_code, vh_ns)
    check_fn = vh_ns["check_external_files_consistency"]
    with tempfile.TemporaryDirectory() as tmp_demo:
        os.makedirs(os.path.join(tmp_demo, "data"), exist_ok=True)
        with open(os.path.join(tmp_demo, "data", "orders.csv"), "w", encoding="utf-8") as f:
            f.write("config_id,status\nCFG-2026-8801,OK\nCFG-2026-8802,OK\n")
        spec_ok = {
            "pdf": {"sections": [{"heading": "Audit", "content": "Checked CFG-2026-8801 and CFG-2026-8802."}], "discrepancy": {}},
            "excel": {"headers": ["id", "config_id"], "rows": [["1", "CFG-2026-8801"], ["2", "CFG-2026-8802"]]},
            "scans": [
                {"title": "Scan 1", "rows": [["1", "K500-ALT", "Obsolete code"]], "is_discrepancy": True},
                {"title": "Scan 2", "rows": [["1", "K999-ERR", "Mismatch"]], "is_discrepancy": True},
            ],
        }
        with open(os.path.join(tmp_demo, "data", "external_files_spec.json"), "w", encoding="utf-8") as f:
            _json.dump(spec_ok, f)
        ok_consistent, msg_consistent = check_fn(tmp_demo)
        failures += check(ok_consistent,
                          "verify_and_heal check_external_files_consistency passes aligned spec",
                          msg_consistent)

        spec_bad = {
            "pdf": {"sections": [{"heading": "Audit", "content": "Checked CFG-2026-8899."}], "discrepancy": {}},
            "excel": {"headers": ["id", "config_id"], "rows": [["1", "CFG-2026-8801"]]},
            "scans": [{"title": "Scan 1", "rows": [["1", "K20", "Standard plate"]], "is_discrepancy": False}],
        }
        spec_bad_path = os.path.join(tmp_demo, "data", "external_files_spec.json")
        with open(spec_bad_path, "w", encoding="utf-8") as f:
            _json.dump(spec_bad, f)
        ok_bad, msg_bad = check_fn(tmp_demo)
        failures += check((not ok_bad) and "CFG-2026-8899" in msg_bad and "Scan #1" in msg_bad,
                          "verify_and_heal flags missing BQ/Excel IDs and non-discrepancy scans",
                          msg_bad)

        # Exercise generate_and_upload_external_files.py's heal_external_files_spec on spec_bad
        gen_lines = gen_src.splitlines()
        gen_tree = ast.parse(gen_src)
        heal_node = next(n for n in gen_tree.body
                         if isinstance(n, ast.FunctionDef) and n.name == "heal_external_files_spec")
        heal_code = "\n".join(gen_lines[heal_node.lineno - 1:heal_node.end_lineno])
        gen_ns = {"os": os, "re": re, "csv": _csv, "glob": _glob, "json": _json, "sys": sys}
        exec(heal_code, gen_ns)
        heal_fn = gen_ns["heal_external_files_spec"]
        repairs = heal_fn(spec_bad, spec_bad_path, os.path.join(tmp_demo, "data"))
        ok_healed, msg_healed = check_fn(tmp_demo)
        failures += check(bool(repairs) and ok_healed,
                          "generate_and_upload_external_files heal_external_files_spec repairs spec_bad cleanly",
                          msg_healed)

    if failures:
        print("\n%d check(s) FAILED" % failures)
        return 1
    print("\nExternal files wiring: all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

