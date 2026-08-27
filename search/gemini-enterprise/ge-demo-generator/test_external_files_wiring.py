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
     v2.9.0 the copy sat inside the `RAG_MODE` branch, so an mcp-mode demo had
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

    python3 test_external_files_wiring.py
"""
import ast
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
SETUP = os.path.join(REPO, "skills/ge-demo-generator/templates/setup_and_deploy.sh")
TOOLS = os.path.join(REPO, "skills/ge-demo-generator/templates/tools.py")
AGENT = os.path.join(REPO, "skills/ge-demo-generator/templates/agent.py")
GEN = os.path.join(REPO, "skills/ge-demo-generator/templates/scripts/"
                         "generate_and_upload_external_files.py")

# The one command that turns a scope-less token into a working Drive upload.
# Both the script and the deploy banner have to print it verbatim, because
# "authorize Drive" sends people to the Cloud console, where it is not.
REAUTH_HINT = "gcloud auth login --enable-gdrive-access"

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
    # summary into it - but it must not reach the container any more.
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

    if failures:
        print("\n%d check(s) FAILED" % failures)
        return 1
    print("\nExternal files wiring: all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
