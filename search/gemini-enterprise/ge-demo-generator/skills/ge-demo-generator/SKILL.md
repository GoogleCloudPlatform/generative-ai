---
name: ge-demo-generator
description: Synthesizes and deploys complete, domain-specific Gemini Enterprise demo environments directly to Google Cloud. Use when the user asks to create an AI agent demo for any customer domain (e.g. 'example.com', 'example.co.jp', 'example.de', 'example.fr' - any company, any industry, any region) or business goal, generate realistic BigQuery/Firestore sample datasets, create external demo files (PDF, Excel, scanned images) and upload them to Google Drive, scaffold ADK multi-agent architectures with MCP tools and A2UI cards, deploy to Cloud Run, publish to Gemini Enterprise, and generate 7 structured demo prompts in any language. Confirms the requirements interactively and presents a demo architecture & data model plan (Mermaid ER diagram, Google Drive file lineage, target project) for approval before anything is deployed. Also triggered by /ge-demo-generator.
metadata:
  author: Google Cloud Customer Engineering
  version: 2.11.0
---

# GE Demo Generator Skill (v2.11.0)

Synthesizes production-grade, domain-tailored AI agent demo environments using **Gemini 3.7 Flash** for reasoning and **Gemini 3.1 Flash Image** for visual generation, adhering to a strict **6-step infrastructure dependency graph**, rich **A2UI interactive component streaming**, **Google Workspace OAuth authorization**, direct **Google Drive external sample files storage**, **7 structured demo prompts**, and **global multilingual localization (i18n/l10n)**.

---

## 🌐 Multilingual Support & Localization Architecture (i18n/l10n)

The skill is implemented entirely in **English** at the system specification and codebase layer, while providing **complete, dynamic multilingual support** for any enterprise domain worldwide:

1. **Automatic Language & Locale Detection**:
   - **From Domain TLD**:
     - `.co.jp`, `.jp`, `.ne.jp`, `.or.jp` ➔ Japanese (`日本語`, `locale: "ja"`, `currency: "JPY"`, `symbol: "¥"`)
     - `.de` ➔ German (`Deutsch`, `locale: "de"`, `currency: "EUR"`, `symbol: "€"`)
     - `.fr` ➔ French (`Français`, `locale: "fr"`, `currency: "EUR"`, `symbol: "€"`)
     - `.es` ➔ Spanish (`Español`, `locale: "es"`, `currency: "EUR"`, `symbol: "€"`)
     - `.it` ➔ Italian (`Italiano`, `locale: "it"`, `currency: "EUR"`, `symbol: "€"`)
     - `.cn`, `.tw` ➔ Chinese (`中文`, `locale: "zh"`, `currency: "CNY"/"TWD"`)
     - `.kr` ➔ Korean (`한국어`, `locale: "ko"`, `currency: "KRW"`, `symbol: "₩"`)
     - `.br` ➔ Portuguese (`Português`, `locale: "pt"`, `currency: "BRL"`, `symbol: "R$"`)
     - `.co.uk`, `.com.au`, `.com`, `.io`, `.org`, etc. ➔ English (`locale: "en"`, `currency: "USD"/"GBP"`)
   - **From User Interaction**:
     - If the user provides a prompt in Japanese, all user-facing demo assets are synthesized in Japanese. If in German, all in German.

2. **Strict Language Consistency Rule (MANDATORY)**:
   - ALL user-facing text elements MUST strictly match the detected target language:
     - Company overview & operational challenges.
     - Table and column business descriptions (harvested into Knowledge Catalog).
     - CSV string values (product names, category names, person names, address strings, remarks).
     - External files: PDF title, body sections, audit summary tables; Excel headers, KPI cards, and notes; Scanned image prompts and handwritten ink text values.
     - System instructions (`businessInstruction`), Welcome Card greeting, and A2UI Button labels.
     - The 7 Structured Demo Prompts (`demoGuide`).
   - **Technical Names Isolation**: Table names, column names, and primary/foreign key ID fields (e.g. `order_id`, `supplier_id`) MUST always remain in English `snake_case` for database engine stability and SQL parser reliability.
   - **Currency symbol**: write the detected symbol to `.env` as `CURRENCY_SYMBOL` (e.g. `CURRENCY_SYMBOL=¥`). The A2UI few-shot examples ship with a literal `[CURRENCY]` placeholder instead of a hardcoded symbol; `setup_and_deploy.sh` substitutes it before the image is built and aborts the deploy if any occurrence survives. Defaults to `$` when unset.

---

## Complete Lifecycle & Infrastructure Dependency Graph

```
Phase 1: Customer Domain & Business Goal Research (Search Grounding & Language Detection)
   ↓
Phase 2: Requirements confirmed interactively ➔ Demo Architecture & Data Model Plan ➔ APPROVAL
   ↓
Phase 3: Synthetic Data & External Sample Files Generation (PDF, Excel, Images) + Google Drive Upload (Step 1/6)
   ↓
Phase 4: ADK Multi-Agent Project Scaffolding & A2UI System Prompts
   ↓
Phase 5: Ordered Cloud Provisioning & Deployment:
   ├── Step 1: BigQuery (with Knowledge Catalog Metadata) & Firestore Initial Data
   ├── Step 2: Agent Engine Sandbox (Code Execution Environment) [CRITICAL DEPENDENCY]
   ├── Step 3: Data Viewer Dashboard Cloud Run Deployment (Gets VIEWER_URL)
   ├── Step 4: Main Multi-Agent Cloud Run Deployment (Injects SANDBOX_RESOURCE_NAME & VIEWER_URL)
   └── Step 5: Background Task Pub/Sub Push Subscription (/execute_task & SELF_URL)
   ↓
Phase 6: Gemini Enterprise App Discovery, Workspace Authorization & Registration (Step 6/6)
   ↓
Phase 7: Comprehensive Results Output:
   ├── 💬 Direct Gemini Enterprise Console Chat Link
   ├── 📁 Google Drive External Sample Files & Folder Links
   ├── 📊 Firestore Data Viewer Dashboard Link
   ├── 🔎 BigQuery Console Link
   └── 🎯 7 Structured Demo Prompts Playbook (Localized to Target Language)
```

---

## Phase 1: Customer Domain & Business Goal Research

1. **Extract Domain & Company**:
   - If a domain is provided (e.g., `example.com`, `example.co.jp`, `example.de`), determine company name, primary industry, and regional language from the domain itself — never from a list baked into this skill.
   - If a business goal or company name is provided, identify the corresponding corporate entity and language.

2. **Grounded Deep Research (via `search_web`)**:
   - Search for the company's latest corporate profile, business units, IR reports, and known operational challenges.
   - Identify:
     - **3-5 Key Business Challenges** (e.g., "yield rate drop in semiconductor fabrication", "supply chain lead-time anomalies").
     - **5-8 Operational Workflows** and evaluate which ones are **automatable** with AI agents.
     - **Authentic Domain Entities & Nomenclature** (e.g., real facility names like "Kumamoto Technology Center", actual product codes, industry status codes).

3. **Interactive Use Case Selection (Customer Domain Selection Flow)**:
   - Present the research findings to the user in their language:
     - 🏢 **Company Profile**: Official name, summary, primary industry.
     - ⚠️ **Key Business Challenges**: 3-5 detected operational pain points.
     - 🎯 **Candidate Workflows**: 3-5 top automatable workflows with automation feasibility ratings.
   - **Prompt the user to select or customize the use case**:
     - Use `ask_question` or present a structured choice so the user can pick the target scenario or write in specific requirements.

---

## Phase 2: Requirements Alignment & Demo Architecture Plan (Approval Gate)

Phase 2 has two steps, in this order and never merged into one:

**Step 2.1 — ask** the handful of questions the design genuinely depends on, interactively.
**Step 2.2 — show** the finished design brief as the alignment artifact, and ask for a go.

The order is what makes the brief worth reading. A brief that still contains open questions
is a questionnaire, and the user has to hold the design in their head while answering it; a
brief written *after* the answers is a mirror — the user is checking whether what you
understood matches what they meant, which is a much easier thing to do and the last cheap
moment to change the entities, the narrative, the file lineage or the target project.

Until the user approves the brief, **nothing is created** — no CSVs, no Drive folder, no
BigQuery dataset, no Cloud Run service. Everything after this point takes 15-30 minutes and
spends real quota in someone's project.

### Step 2.1 — Confirm the requirements interactively

Ask only what you cannot responsibly decide, and ask it *before* writing the brief. Keep it
short — two to four questions, batched into one message (`ask_question` where available), each
with a stated default so the user can answer "all defaults" in three words:

1. **Anchor persona** — who is the primary user of this agent (job title, and a sentence of
   context if useful)? That persona becomes the demo's protagonist: the agent is framed as
   *their* process operator, prompt 1 opens from their daily situation, approval gates are
   decisions they or their manager own, and every other persona appears only as a hand-off
   counterpart. If the user declines, rotate personas freely instead.
2. **Scope of the narrative** — which single process instance the demo follows, if Phase 1
   left more than one plausible reading of the chosen scenario.
3. **Advanced settings** — the options from the table in brief section 6 that this demo is a
   plausible candidate for, with their defaults. Do not read out all eight; name the two or
   three that matter here (Workspace OAuth when the scenario touches Gmail/Drive/Calendar,
   `rag` when it turns on documents rather than numbers, `dataScale` when the narrative claims
   enterprise volume) and say the rest keep their defaults.
4. **Target environment** — only if what `gcloud` reports (read it now, see below) is not
   obviously the project the user means.

Anything the user has already stated — in the original request or in Phase 1 — is *decided*.
Re-asking it reads as not having listened.

**Read the target environment** before writing the brief, so its section 5 states facts rather
than intentions:

```bash
GCP_ACCOUNT=$(gcloud config get-value account 2>/dev/null || echo "Unknown")
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
REGION=${CLOUD_RUN_REGION:-"asia-northeast1"}
```

### Step 2.2 — Present the Demo Architecture & Data Model Plan

One message, six sections, in this order, then the gate. Every answer from Step 2.1 is already
folded in — the brief **states** decisions, it does not ask for them, and it contains no
"tell me which…" or "TBD" anywhere.

Write it in **the demo's language** (§ i18n above) — headings, table headers and prose alike.
Only the technical identifiers stay English `snake_case`: table names, column names and
`.env` keys.

Open with a title line naming the company and the selected scenario, so the brief is
self-contained when it is pasted into a chat with a colleague:

> ### 🏗️ `<Company>` — Demo Architecture & Data Model Plan
> Based on the selected scenario **"`<scenario>`"**, here is the data layer design, the
> Mermaid ER diagram and the cross-source reconciliation lineage.

### § Brief section 1 — 🏢 Target Company & Demo Overview

- **Company / group**: official name, and the group entity the demo actually models.
- **Industry**: the specific one, in the company's own vocabulary.
- **Demo narrative**: 2-3 sentences following **one** business process instance (one
  problematic order, one flagged application) end to end, naming the departments it passes
  through. All 7 demo prompts later trace this same instance; see
  `references/demo_prompts_guide.md` §1.1-§1.2.
- **Anchor persona**: the persona confirmed in Step 2.1, stated as a fact ("the agent is
  operated by the production control manager of the main works"). If the user declined to
  name one, say that personas rotate instead — do not re-ask here.

### § Brief section 2 — 📊 Data Layer Design & Mermaid ER Diagram

- **Render a Mermaid `erDiagram`** in a ```mermaid fenced block: every table, every column
  with its type, `PK`/`FK` markers, cardinality labels on each relationship, and a short
  business gloss in quotes after each column (`string order_id PK "order number (ORD-2026-XXXX)"`).
  The gloss is the same sentence that later becomes the column description in the Knowledge
  Catalog, so writing it here is not duplicated work.
- Include the Firestore task collection as an entity too — it is part of the model the demo
  reasons over, even though it is not in BigQuery.
- **Shared core-system model**: design the tables as a slice of the company's system of
  record, not one team's dataset — a transactional table two departments both write, a
  rules/threshold table owned by one department that another's workflow must consult, and
  an audit seed visible only when the departments' views are joined. Details and the
  single-department escape hatch: `references/data_generation.md` §1.3.

### § Brief section 3 — 📁 Google Drive External Files & Cross-Source Lineage

A table with one row per external file — type, filename, and what binds it to BigQuery:

| External file | Filename | Content & data binding |
|---|---|---|
| 📄 PDF audit report | `<domain>_audit_report.pdf` | which tables it summarizes, and the deliberate 5-15% variance that makes cross-source reconciliation necessary |
| 📊 Excel ledger | `<domain>_external_ledger.xlsx` | which FK column it joins on, and the row count |
| 🖼️ Scanned form 1 | `handwritten_order_1.jpg` | what the form is, in-domain, generated by `gemini-3.1-flash-image` |
| 🖼️ Scanned form 2 | `handwritten_order_2.jpg` | the second form, and the discrepancy it carries |

State the join key explicitly. A lineage row that says "related to orders" is not a design —
the whole point of the external files is that a question can only be answered by reading a
document *and* querying a table, and that only works if the keys line up (70%+ FK match,
5-15% audit variance). See `references/external_files_and_drive.md`.

Close the section with where the files will actually live, in one line, because it is the
part users assume wrongly: they are staged to `gs://<project>-<domain>-<suffix>-docs/` in
every mode; at deploy time the `gdrive` CLI uploads them into the Drive of whoever is
running this skill and shares that folder with `${GCP_ACCOUNT}` as Writer; and when the
CLI is not available or not signed in, there is no Drive copy at all — the deploy banner
says so, and the documents are reachable only from Cloud Storage and `./external_files/`.
The deployed agent has no way to put them in anyone's Drive. If the user wants them in
Drive and has no working `gdrive` CLI, say so here, while it can still be sorted out.

### § Brief section 4 — 🤖 Agent Models & Runtime

- **Reasoning / orchestration**: **`gemini-3.7-flash`** for all agent instances (Root
  Coordinator, Deep Analysis Sub-Agent, Background Worker).
- **Image generation**: **`gemini-3.1-flash-image`** (with localized prompt reinforcement and
  GCS artifact persistence).
- **Code execution**: Agent Engine Sandbox (`us-central1` — fixed, not `$REGION`).
- **UI**: Gemini Enterprise A2UI v0.9 composite catalog (name the components this demo will
  actually lean on — `MaterialTable`, `VegaChart`, `MaterialCard`).

### § Brief section 5 — ⚙️ Deployment Target Environment

Show what the commands above returned, verbatim, in a fenced block:

```
👤 Active User Account : ${GCP_ACCOUNT}
🏢 Target Project      : ${PROJECT_ID} (${PROJECT_NUMBER})
🌐 Target Region       : ${REGION}
📁 Google Drive Storage: Google Drive of ${GCP_ACCOUNT}
```

This is the section users most often stop on, because the answer is frequently "wrong
project". Do not paraphrase the values and do not print a project the user named unless
`gcloud` agrees — the deploy will use what `gcloud` says, not what the brief claims. The Drive
line is only true when the `gdrive` CLI is authenticated as the same account. When the CLI is
signed in as someone else, that account owns the folder and `${GCP_ACCOUNT}` gets it as a
share, so write `📁 Google Drive Storage: Google Drive of <gdrive account>, shared with
${GCP_ACCOUNT}`; when there is no CLI at all, write `📁 Google Drive Storage: staged in GCS;
imported into the Drive of ${GCP_ACCOUNT} on the first message to the agent`. See
`references/external_files_and_drive.md` §5. Never print a Drive destination the deploy
cannot reach.

### § Brief section 6 — 🎛️ Advanced Settings & Integrations

   State the settings **this** demo will deploy with — the answers from Step 2.1, plus the
   defaults for everything the user did not touch. These names are the `.env` keys,
   upper-snake-cased: `enableManagedAgent` is `ENABLE_MANAGED_AGENT`. Every one of them is a
   real switch in the deployed container, so an option discussed here but not written to
   `.env` is a feature the demo will not have.

   | Option | Default | What it buys, and what it costs |
   |---|---|---|
   | 🤖 `enableManagedAgent` | **`true`** | Agent Engine Sandbox code execution, asynchronous background delegation (`delegate_autonomous_task`), scheduled tasks and Drive deliverable exports. The delegation prompts in the demo playbook exercise this, which is why it is the one default-on capability. Adds ~8-10 min of provisioning, overlapped with the rest of the deploy. |
   | 🔎 `dataExplorationMode` | **`mcp`** | How the agent reads the demo's data. **`mcp`** (default) provisions no search index: the data-asset catalog is already in the agent's system instruction, so a figure question is *one* `execute_sql` call — the four-to-five round trips people blame on "no index" came from the metadata expedition in front of the query, and the mcp routing block overrides exactly that. **`rag`** additionally builds a Discovery Engine index over the BigQuery dataset and the staged files and makes it the read path: lookups and document questions return in one sub-second `search_datastore` call, while computed figures, joins and every write stay on MCP because the index lags the tables. Pick `rag` when the demo turns on documents rather than on numbers, and note it also attaches data stores to the (often shared) Gemini Enterprise app — see `references/datastore_connectors.md`. |
   | 🔑 `enableWorkspaceAuth` | `false` | User-OAuth passthrough — the agent acts as the signed-in user for the Drive handoff and Workspace token plumbing. Commonly wanted, since Workspace is usually available in the target environment, but **not** default-on: some organizations refuse to authorize an OAuth client they have not vetted, and there sign-in fails for every demo user. Confirm the target org permits it before enabling. |
   | 🔑 `enableWorkspaceMcp` | `false` | **Advanced, rarely used.** Adds the Gmail / Drive / Calendar / Docs / Chat MCP toolsets on top of the auth passthrough. The Workspace MCP servers are Developer Preview and the project must be allowlisted first — enable it without that and every Workspace call 403s. Kept separate from `enableWorkspaceAuth` for exactly this reason. |
   | 🖥️ `enableComputerUse` | `false` | Headless browser automation (Playwright). Also requires uncommenting the Playwright block in **both** `requirements.txt` and the `Dockerfile`; the deploy pre-flights this and refuses a half-configured build. |
   | 📦 `customMcpRepos` | empty | Third-party MCP servers. Both GitHub sidecars and remote managed servers (Slack included — it is one entry in this list, not a flag of its own) go here. |
   | 🌐 `publicDatasetId` | unset | Ground the demo in a real BigQuery public dataset (e.g. NOAA Weather, Google Trends) alongside the synthetic data. |
   | 📈 `dataScale` | unset (hero rows only) | Row count to grow the fact tables to before loading — thousands to tens of thousands. You still write only the 50-200 hero rows the demo script names; `scripts/amplify_data.py` expands the tables around them deterministically, keeping the hero rows verbatim and foreign keys intact. Ask for it when the narrative claims enterprise volume or the demo opens with an aggregate — a `COUNT(*)` of 63 undercuts both. Costs ~10-30s of setup and a longer Discovery Engine ingest. |

Only list the options that are on, plus the two or three the demo is a plausible candidate
for. A user reading eight defaults they did not ask about is a user who skims the whole brief.

### § The gate — ask once, then stop

Close the message with a single explicit question, in the demo's language, that (a) names what
approving will run — synthetic data generation, Google Drive upload, Cloud Run deploy, Gemini
Enterprise registration (Phases 3-7) — and (b) leaves the door open for late changes:

> Shall I proceed with this design and run the synthetic data generation, Google Drive upload,
> Cloud Run deployment and Gemini Enterprise registration (Phases 3-7) in one pass? Let me know
> if you want any option enabled (Google Workspace OAuth, RAG mode, data scale, …) or any part
> of the model changed.

One question, not a second round of Step 2.1: everything else was settled before the brief was
written, and a gate that re-opens five decisions is a gate nobody clears.

Then **stop and wait**. Do not start Phase 3 in the same turn, and do not treat "looks good" on
a *previous* message — the scenario choice in Phase 1 or an answer in Step 2.1 — as approval of
this brief.

When the user changes something, re-render the affected sections and ask again; an approved
brief is the specification the rest of the run is built from, so it has to be the version the
user actually said yes to.

---

## Phase 3: Synthetic Data & External Sample Files Generation + Google Drive Upload

**Entry condition: the Phase 2 brief was presented in full and the user approved it.** If you
arrive here without that, go back and present it.

1. **Derive the demo's identifiers** (the account, project, number and region were already read
   and shown in brief section 5 — re-read them here only if the shell state was lost):
   ```bash
   SUFFIX=$(date +%s | tail -c 5)
   DATASET_ID="demo_${DOMAIN_SLUG}_${SUFFIX}"
   FIRESTORE_COLLECTION="demo-${DOMAIN_SLUG}-${SUFFIX}-tasks"
   ```

2. **Generate Real-World Synthetic Data & Display Previews**:
   - Generate CSV files with realistic addresses, valid foreign keys across tables, and varied statuses in `data/<table_name>.csv`.
   - Ensure all string data is generated in the detected target language.
   - Run validation script: `python3 scripts/validate_csv.py data/*.csv`.
   - **Render Dataset Preview & Record Counts**: Output a Dataset Summary Table with total generated record counts for each BigQuery table, Firestore collection, and external Drive file, followed by 3–5 representative sample rows per table in clean Markdown preview tables (or `<carousel>` sliders) clearly indicating the total row count in each table title.
   - Write one line of grain per table into `data/<table_name>_description.txt` ("one row per
     POS transaction line", "one row per store"). The deploy folds it, the column
     descriptions from `data/<table_name>_schema.json`, the row counts and the real date
     range of every date column into `adk_agent/app/data_assets.md` — the DATA ASSET CATALOG
     the agent's prompt is written around. Skipping the grain line costs only that line;
     skipping the column descriptions costs the agent its schema.

2b. **Amplify to Demo Volume (only when `dataScale` was agreed in Phase 2)**:
- Do **not** try to write thousands of rows yourself. Write the 50-200 hero rows as
  above — the ones the demo prompts name by id — and let the amplifier expand the
  tables around them. It resamples each column from what the hero rows already show,
  draws foreign keys from the parent table's amplified key set, and keeps the hero
  rows verbatim at the top of every file, so every id a prompt refers to still resolves.
- Write `data/data_scale_spec.json` with a per-table `target_rows` map. Describe a
  column only where the hero rows misrepresent it — in practice that means date
  columns, because hand-written rows cluster into one week while the narrative spans
  a fiscal year. Everything you leave out is inferred. See the module docstring of
  `scripts/amplify_data.py` for the format and for the two things the spec will not do.
  ```bash
  python3 scripts/amplify_data.py --data-dir ./data --spec ./data/data_scale_spec.json
  for f in data/*.csv; do case "$f" in *.hero.csv) ;; *) python3 scripts/validate_csv.py "$f" ;; esac; done
  ```
- Alternatively set `DATA_SCALE=<rows>` in `.env` and let the deploy run it: the step
  is idempotent and deterministic, so doing it in both places is harmless.
- Report the amplified counts in the Dataset Summary Table, and say which tables were
  left at hero size — master data that the narrative describes as small must stay small.
- `python3 scripts/amplify_data.py --data-dir ./data --restore` puts the hero CSVs back.

3. **Generate External Sample Files & Upload Directly to Google Drive**:
   - Synthesize external demo files in `./external_files/`:
     1. **PDF Audit Report** (`<domain>_audit_report.pdf`): Multi-section structured document in target language with summary, details, and intentional 5-15% variance from BigQuery to trigger cross-source reasoning.
     2. **Excel Spreadsheet Ledger** (`<domain>_external_ledger.xlsx`): Semi-structured workbook with localized KPI headers, units, and 40-80 transaction rows with FK references matching BigQuery tables.
     3. **Simulated Operational Document Images** (`handwritten_order_1.jpg`, `handwritten_order_2.jpg`): Realistic scanned forms generated via `gemini-3.1-flash-image` with localized text.
   - **Upload to Google Drive**:
     ```bash
     uv run --with "openpyxl,reportlab,pillow" python3 scripts/generate_and_upload_external_files.py \
       --domain "$DOMAIN_SLUG" \
       --company "$COMPANY_NAME" \
       --suffix "$SUFFIX" \
       --outdir "./external_files" \
       --spec-file "./data/external_files_spec.json"
     ```
     - `--spec-file` carries THIS demo's content (titles, sections, table rows, and the
       `style` wording for the scanned forms), written in the demo's own language and
       domain. Without it the script emits generic placeholder documents - it holds no
       built-in industry content by design.
     - Creates dedicated Drive folder: `GE Demo - <Company Name> (<Suffix>)`.
     - Uploads `.pdf`, `.xlsx`, and `.jpg` files.
     - Saves links to `external_files/drive_upload_summary.json` and creates `.url.json` artifacts.
     - **The folder lands in the Drive of whoever the `gdrive` CLI is signed in as** — a
       CLI owns what it creates — **and the deploy target is added as Writer** with
       `mutate share --email <target> --role writer --notify=false`, so it shows up under
       that account's "Shared with me". Report the owner, the share recipient, and the
       folder URL; when the share itself failed (cross-domain sharing is often blocked by
       policy), the summary carries `share_error` and the banner says `❗ SHARING FAILED`
       — pass that on with the manual share command rather than handing over a link the
       target cannot open.
     - When there is no authenticated `gdrive` CLI the upload is skipped and the summary
       carries `skip_reason`. The documents are not lost — `setup_and_deploy.sh` stages
       every file to `gs://$GCS_BUCKET_NAME/` in **both** data-exploration modes — but
       there will be no Drive folder, and nothing downstream creates one: report the
       skip and its reason on the completion screen, point at the Cloud Storage links,
       and say what to do to get a folder (sign the `gdrive` CLI in and re-run, or upload
       `./external_files/` by hand). See `references/external_files_and_drive.md` §5.

4. **Provision BigQuery Dataset & Tables (Step 1/6)** (Idempotent + Knowledge Catalog Metadata):
   ```bash
   # US, not $REGION: a dataset's location is fixed at creation, the Discovery
   # Engine BigQuery connector imports from a global datastore, and the public
   # datasets a demo may join against (bigquery-public-data) live in US.
   bq show "${PROJECT_ID}:${DATASET_ID}" >/dev/null 2>&1 || bq --location=US mk -d "${PROJECT_ID}:${DATASET_ID}"
   for f in data/*.csv; do
     tbl=$(basename "$f" .csv)
     bq load --source_format=CSV --autodetect --skip_leading_rows=1 --replace "${DATASET_ID}.${tbl}" "$f"
     if [ -f "data/${tbl}_schema.json" ]; then
       bq update "${DATASET_ID}.${tbl}" "data/${tbl}_schema.json" >/dev/null 2>&1 || true
     fi
   done
   ```

5. **Initialize Firestore Collection**:
   - Write 5-10 initial operational documents - task queues, anomalies, approvals pending -
     to `data/firestore_seed.json` as a list of `{"id": ..., "data": {...}}` objects, in the
     demo's own language and domain, then upload them:
     ```bash
     uv run --with "google-cloud-firestore" python3 scripts/setup_fs.py \
       --collection "$FIRESTORE_COLLECTION" \
       --docs ./data/firestore_seed.json
     ```
   - `scripts/setup_fs.py` holds no seed content itself; see its module docstring for the
     expected document shape.

---

## Phase 4: ADK Multi-Agent Project Scaffolding & System Instructions

Scaffold the project in `./ge-demo-<domain>-<suffix>/`.

**Do not retype these files.** Copy them from this skill's `templates/` directory, which is
the single source of truth for every scaffolded file, then edit only the placeholders each
file marks. `templates/` mirrors the tree below one-for-one (`templates/agent.py` ->
`adk_agent/app/agent.py`, `templates/scripts/` -> `scripts/`, and so on):

```
ge-demo-<domain>-<suffix>/
├── adk_agent/
│   ├── __init__.py            # empty; makes adk_agent importable as a package
│   └── app/
│       ├── __init__.py
│       ├── agent.py           # Triple-Agent (gemini-3.7-flash) + Code Executor + A2UI System Prompts
│       ├── tools.py           # MCP Toolsets + gemini-3.1-flash-image generate_image tool
│       ├── part_converters.py # A2A <-> Gen AI DataPart Converters
│       ├── fast_api_app.py    # A2A Server + A2UI StreamParser + Token Middleware + /execute_task
│       ├── data_assets.md     # DATA ASSET CATALOG (written at deploy time; do not hand-edit)
│       ├── catalogs/          # A2UI v0.9 Gemini Enterprise composite catalog
│       └── examples/0.9/      # A2UI few-shot example surfaces
├── viewer_app/                # Real-Time Operations Viewer Flask App
│   ├── main.py
│   └── requirements.txt
├── data/                      # Generated CSV files + Knowledge Catalog schemas
├── external_files/            # Generated PDF, Excel & Scanned Images
├── scripts/
│   ├── managed_agent_instruction.txt # Autonomous sandbox agent's system instruction
│   ├── validate_csv.py        # CSV formatting & schema auto-repair
│   ├── amplify_data.py        # Grows hero CSVs to demo volume (deterministic, FK-safe)
│   ├── build_data_catalog.py  # CSVs -> adk_agent/app/data_assets.md (the agent's schema)
│   ├── generate_and_upload_external_files.py # External files & Google Drive uploader
│   ├── setup_fs.py            # Firestore seed documents
│   ├── setup_datastores.py    # Discovery Engine DataStore creation & import
│   ├── register_agent.py      # Gemini Enterprise agent registration
│   ├── create_managed_agent.py / warmup_managed_agent.py # Agent Engine managed agent
│   ├── dep_smoke_test.py      # Pinned-dependency import smoke test
│   ├── preflight_check.py     # Pre-deploy static checks
│   ├── verify_and_heal.py     # Post-deploy verification & auto-repair
│   └── cleanup.sh             # One-click teardown (Cloud Run, Agent Engine Sandbox, Managed Agent, BQ, FS, GCS)
├── .env                       # Configuration shared by setup_and_deploy.sh and cleanup.sh
│                              # (full key reference: references/deployment_and_iam.md §3)
├── Dockerfile                 # Multi-stage container build
├── requirements.txt           # Python dependencies
└── setup_and_deploy.sh        # Standalone reproducible deployment script (strictly ordered)
```

**Two files carry this demo's domain knowledge and BOTH must be filled in:**

1. `adk_agent/app/agent.py` - the `gen_instruction` block, marked
   `TEMPLATE PLACEHOLDER`. This is the conversational agent's business context.
2. `scripts/managed_agent_instruction.txt` - the same context for the autonomous
   sandbox agent, in its `[BUSINESS_CONTEXT]` slot. Leave the file untouched and
   `enableManagedAgent` - the one default-on capability - is *silently skipped*
   at deploy time, taking `delegate_autonomous_task` and demo prompts 5 and 7
   with it. `[DATASET_ID]` and `[COLLECTION_ID]` are substituted by
   `setup_and_deploy.sh`; leave those alone. When a Workspace, computer-use or
   operating-model option is on, the matching block has to be added too - see
   `references/multi_agent_architecture.md` §4.

### Critical A2UI System Instruction Requirements (v0.9 Composite Catalog)
1. **Output Placement Rule (Rule #0)**: Any text in the same response turn as a tool call is hidden. Only output `🔍 Analyzing...` during tool execution. Final analytical reports, A2UI cards, and chips MUST appear in a separate turn with ZERO tool calls.
2. **Mandatory A2UI Cards (v0.9 Standard)**: Plain text markdown tables and bullet lists are forbidden for data presentation. Wrap results in `<a2ui-json> ... </a2ui-json>` using `MaterialCard`, `MaterialTable`, `VegaChart`, `MaterialRow`, `MaterialColumn`, and `MaterialDivider`.
3. **A2UI v0.9 Component Model (CRITICAL)**:
   - Every message stamped with `"version": "v0.9"`.
   - `createSurface` has **NO `root` key**: `{"version": "v0.9", "createSurface": {"surfaceId": "...", "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"}}`.
   - Root component MUST have `id: "root"`.
   - Components use flat type names (`"component": "MaterialButton"`), plain strings (`"title": "..."`), and plain arrays (`"children": ["id1", "id2"]`).
   - `MaterialButton` has a flat `label: "..."` and event action: `{"action": {"event": {"name": "action_name", "context": {"prompt": "User message prompt"}}}}`.
4. **Welcome Card on Greeting**: On initial turn / greeting, DO NOT call tools. Output ONE line of plain-text greeting in user's language, followed by `<a2ui-json>` onboarding card with surfaceId `welcome-card` and 3 action buttons. Do not emit suggestion chips on the welcome turn.
5. **Suggestion Chips**: Append 3-4 follow-up `MaterialButton`s with `action.event.context.prompt` at the end of every normal response, ALWAYS in their own trailing surface with surfaceId `suggestions`, emitted after the card — never as a `MaterialRow` inside the card. A turn's second A2UI surface does render; the rule that once said otherwise was wrong. Keeping the follow-ups out of the card keeps the answer card a clean read and makes the next actions a footer under it. (This layout is *not* a scroll fix — a press scrolls to the element of the user's PREVIOUS press, which no arrangement of surfaces can change; the server retires the pressed surface instead, see `references/a2ui_catalog.md`.) For the same readability reason a card carries no footer action row of its own — the exceptions are a button bound to its own card's fields (a binding only resolves within its surface) and the welcome card, whose buttons are its own content and which opens the conversation.

---

## Phase 5: High-Speed & Resilient Deployment Sequence (Zero-Timeout)

Follow the optimized dependency sequence with local pre-flight checks and fast builds:

1. **Step 0: Local Pre-flight Verification (1-Second Syntax & Import Check)**:
   *Prevents 5-minute remote Cloud Build / Cloud Run startup health check timeouts by catching syntax/import errors instantly.*
   ```bash
   python3 scripts/preflight_check.py
   ```

2. **Step 2/6: Provision Agent Engine Sandbox (Code Execution Environment)**:
   *Must be executed from a clean temporary directory (`mktemp -d`) to prevent SDK build hangs.*
   *The heredoc runs in a child process, so the variables it reads must be **exported** — a plain
   `source .env` leaves them shell-local and every `os.environ.get()` below silently returns the default.*
   ```bash
   set -a; [ -f .env ] && source .env; set +a
   export PROJECT_ID SERVICE_NAME
   SANDBOX_TMPDIR=$(mktemp -d)
   pushd "$SANDBOX_TMPDIR" > /dev/null
   python3 - << '__SANDBOX_EOF__'
   import os, vertexai
   from vertexai import types
   client = vertexai.Client(project=os.environ.get('PROJECT_ID', ''), location='us-central1')
   ae = client.agent_engines.create(config={'display_name': os.environ.get('SERVICE_NAME', 'demo') + '-sandbox'})
   sb = client.agent_engines.sandboxes.create(
       name=ae.api_resource.name,
       config=types.CreateAgentEngineSandboxConfig(display_name='code-sandbox'),
       spec={'code_execution_environment': {}}
   )
   with open('/tmp/sb_out.txt', 'w') as f:
       f.write(f"{ae.api_resource.name}|{sb.response.name}")
   __SANDBOX_EOF__
   popd > /dev/null
   rm -rf "$SANDBOX_TMPDIR"
   AGENT_ENGINE_NAME=$(cat /tmp/sb_out.txt | cut -d'|' -f1)
   SANDBOX_RESOURCE_NAME=$(cat /tmp/sb_out.txt | cut -d'|' -f2)
   ```

3. **Step 3/6: Deploy Data Viewer Dashboard (Cloud Run with --no-allow-unauthenticated + IAP)**:
   *The service name MUST be `ge-viewer-${SERVICE_NAME}`. `scripts/cleanup.sh` reconstructs it
   from that exact expression; any other name leaves the viewer running and billing after teardown.*
   ```bash
   VIEWER_SERVICE_NAME="ge-viewer-${SERVICE_NAME}"
   gcloud run deploy "$VIEWER_SERVICE_NAME" \
     --source viewer_app \
     --region "$REGION" \
     --platform managed \
     --ingress all \
     --no-allow-unauthenticated \
     --set-env-vars="PROJECT_ID=${PROJECT_ID},FIRESTORE_COLLECTION=${FIRESTORE_COLLECTION},DEMO_ID=${DEMO_ID},DASHBOARD_TITLE=${DOMAIN_SLUG} Operations Console,SYSTEM_DESCRIPTION=Real-Time Operational Intelligence Dashboard"

   # Enable IAP and grant deployer access
   PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
   gcloud beta services identity create --service=iap.googleapis.com --project="$PROJECT_ID" >/dev/null 2>&1 || true
   gcloud run services add-iam-policy-binding "$VIEWER_SERVICE_NAME" --region="$REGION" --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" --role="roles/run.invoker" --project="$PROJECT_ID" >/dev/null 2>&1 || true
   gcloud beta run services update "$VIEWER_SERVICE_NAME" --region="$REGION" --iap --project="$PROJECT_ID"
   DEPLOYER_EMAIL=$(gcloud config get-value account 2>/dev/null)
   if [ -n "$DEPLOYER_EMAIL" ]; then
     gcloud beta iap web add-iam-policy-binding --project="$PROJECT_ID" --resource-type=cloud-run --region="$REGION" --service="$VIEWER_SERVICE_NAME" --member="user:$DEPLOYER_EMAIL" --role="roles/iap.httpsResourceAccessor" >/dev/null 2>&1 || true
   fi
   VIEWER_URL=$(gcloud run services describe "$VIEWER_SERVICE_NAME" --region="$REGION" --format="value(status.url)")
   ```

4. **Step 4/6: Deploy Main Multi-Agent Service (Cloud Run with uv Acceleration)**:
   *Uses uv inside Dockerfile to slash Cloud Build container creation time from ~4 minutes to ~20 seconds.*

   > [!IMPORTANT]
   > **Every capability in this runtime is switched on by an environment variable, not by the
   > code that was shipped.** The templates read their flags at import time, so a variable you
   > do not pass is not "left at its default" — it is OFF, and the matching tool answers
   > `{"status": "unavailable"}` for the life of the demo. `setup_and_deploy.sh` builds the
   > full list in `$CR_ENV_VARS`; run the script rather than retyping it. The abbreviated
   > command below is for understanding the shape, not for copying.

   ```bash
   # setup_and_deploy.sh assembles this; see references/deployment_and_iam.md for the
   # complete table and for which variables are applied later, in Step 5.
   MIN_INSTANCES="${MIN_INSTANCES:-0}"   # export MIN_INSTANCES=1 to stay warm for a live demo
   gcloud run deploy "$SERVICE_NAME" \
     --source . \
     --region "$REGION" \
     --platform managed \
     --memory 8Gi \
     --cpu 2 \
     --no-cpu-throttling \
     --cpu-boost \
     --min-instances "$MIN_INSTANCES" \
     --max-instances 1 \
     --timeout 1800 \
     --no-allow-unauthenticated \
     --ingress internal \
     --labels "created-by=adk" \
     --set-env-vars="$CR_ENV_VARS" \
     --quiet \
     $SECRETS_FLAG
   SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)")
   ```

   `$CR_ENV_VARS` carries, at minimum: `PROJECT_ID`, `GOOGLE_CLOUD_PROJECT`,
   `GOOGLE_CLOUD_LOCATION=global`, `BIGQUERY_DATASET`, `FIRESTORE_COLLECTION`, `DEMO_ID`,
   `SANDBOX_RESOURCE_NAME`, `AGENT_ENGINE_NAME`, `DATA_VIEWER_URL`, `GEMINI_AUTHORIZATION_ID`,
   `DASHBOARDS_BUCKET`, `RUNTIME_SA_EMAIL`, `WORKER_QUEUE`, `WORKER_QUEUE_LOCATION`, the two
   `ADK_*` compatibility switches, the five `ENABLE_*` flags in their `1`/`0` form, and
   `MANAGED_AGENT_ID` / `MANAGED_AGENT_SKILLS_SOURCE` when the autonomous agent is on.
   `$SECRETS_FLAG` binds `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` from Secret Manager when
   either Workspace flag is set.

5. **Step 5/6: Finalize Background Task Infrastructure & Post-Deploy Wire-up**:
   *Background runs travel over Cloud Tasks, not an in-process self-call: the service deploys
   with `--min-instances 0`, so a localhost fallback would die with the turn that started it
   and could never wake a cold instance.*
   ```bash
   SCHED_TOPIC="${SERVICE_NAME}-sched-topic"
   gcloud pubsub topics create "$SCHED_TOPIC" --project="$PROJECT_ID" 2>/dev/null || true
   gcloud pubsub subscriptions create "${SCHED_TOPIC}-push" \
     --topic="$SCHED_TOPIC" \
     --push-endpoint="${SERVICE_URL}/execute_task" \
     --push-auth-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
     --ack-deadline=600 \
     --project="$PROJECT_ID" 2>/dev/null || true

   # max-concurrent-dispatches matches the runtime's worker semaphore, so work waits in
   # the queue instead of piling up inside one container.
   gcloud tasks queues create "$WORKER_QUEUE" \
     --location="$WORKER_QUEUE_LOCATION" \
     --max-attempts=5 --max-concurrent-dispatches=2 --max-dispatches-per-second=5 \
     --min-backoff=15s --max-backoff=300s \
     --project="$PROJECT_ID" 2>/dev/null || true

   # Values that cannot exist until after the deploy: the assigned service URL, the
   # Gemini Enterprise app discovered in Phase 6, and the warmed sandbox environment.
   gcloud run services update "$SERVICE_NAME" \
     --update-env-vars="SELF_URL=${SERVICE_URL},GEMINI_ENTERPRISE_APP_ID=${SELECTED_APP_ID},DATASTORE_LOCATION=${SELECTED_LOC}" \
     --region="$REGION" \
     --quiet 2>/dev/null || true
   ```

---

## Phase 6: Gemini Enterprise App Discovery, Authorization & Registration (Step 6/6)

1. **Check Discovery Engine / Gemini Enterprise App Existence**:
   - Query Discovery Engine API across regions (`global`, `us`, `eu`).
   - If 1 GE App found: select it automatically.
   - If 0 GE Apps found: automatically create `default-gemini-enterprise-app` via Discovery Engine API.

2. **Google Workspace OAuth Authorization Linking (when either `enableWorkspaceAuth` or `enableWorkspaceMcp` is on)**:
   - Check Secret Manager for `ge-demo-oauth-client-id` and `ge-demo-oauth-client-secret`.
   - If missing, guide user through step-by-step setup in Console and save credentials.
   - Create Discovery Engine Authorization resource with stored credentials.
   - Pass `--authorization-id=projects/$PROJECT_ID/locations/global/authorizations/$AUTH_ID` during registration.

3. **Register Agent to Gemini Enterprise**:
   ```bash
   # Discovery Engine Service Account permissions
   gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
     --region="$REGION" \
     --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
     --role="roles/run.servicesInvoker"

   # Register via agents-cli
   agents-cli publish gemini-enterprise \
     --agent-card-url "${SERVICE_URL}/a2a/app/.well-known/agent-card.json" \
     --display-name "${COMPANY_NAME} Demo Agent" \
     --description "${DEMO_DESCRIPTION}" \
     ${AUTH_FLAG}
   ```

---

## Phase 6.5: Autonomous Verification & Real-Time Self-Healing Engine (Mandatory Gate)

Immediately after deployment and registration complete, execute the automated 8-layer verification and self-healing engine before presenting results to the user:

```bash
python3 scripts/verify_and_heal.py
```

### The 8-Layer Autonomous Verification & Healing Matrix
1. **Layer 1: BigQuery Schema & Primary Keys**: Inspects all tables in `${DATASET_ID}`, verifies row counts, and **auto-heals** missing `_id` document columns (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS _id STRING; UPDATE ... SET _id = <PK>`) to guarantee Discovery Engine DataStore ingestion compatibility.
2. **Layer 2: Firestore Operations Collection**: Verifies operational task documents count >= 3. Auto-seeds initial documents if missing.
3. **Layer 3: Data Viewer & IAP**: Verifies Cloud Run dashboard service status and guarantees `roles/run.invoker` binding for `service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com`.
4. **Layer 4: Agent Engine Sandbox**: Confirms Agent Engine Code Sandbox resource accessibility.
5. **Layer 5: Cloud Run A2A & Fallback Routing**: Probes `/openapi.json`, `/a2a/app/.well-known/agent-card.json`, and root POST fallback alias `@app_instance.post("/")`.
6. **Layer 6: Discovery Engine DataStores & Engine Binding**: Inspects indexed document count in `ds-<service>-bq` and `ds-<service>-gcs`, auto-restarts table ingestion if 0 documents, and verifies `dataStoreIds` attachment on the Gemini Enterprise Assistant Engine.
7. **Layer 7: Agent Registry URL & Authorization**: Verifies registered agent URL strictly ends with `/a2a/app`, auto-patches Gemini Enterprise agent card if missing, and verifies Authorization resource formatting (`projects/${PROJECT_NUMBER}/...`). Resolves direct chat link `https://vertexaisearch.cloud.google.com/home/cid/${CONFIG_ID}/r/agent/${AGENT_ID}/session/-`.
8. **Layer 8: External Files & Google Drive**: Verifies external PDF, Excel, and Scanned Image files staging.

---

## Phase 7: Comprehensive Results Output & 7 Demo Prompts Playbook

Upon deployment completion, ALWAYS output the structured results containing direct links and the **7 Structured Demo Prompts Playbook** localized into the customer's target language:

### 1. Deployment Identity & Direct Links Section
```markdown
### 👤 Deployment Identity & Environment
- 👤 **Deployed By Account**: `${GCP_ACCOUNT}`
- 🏢 **Target Project**: `${PROJECT_ID}` (Project Number: `${PROJECT_NUMBER}`)
- 🌐 **Deployed Region**: `${REGION}`
- 🤖 **Cloud Run Service Account**: `${PROJECT_NUMBER}-compute@developer.gserviceaccount.com`

---

### 🔗 Quick Access Links
> [!IMPORTANT]
> **Account Notice:**
> Open these links in a browser whose Google Cloud / Workspace session is the deploying account **`${GCP_ACCOUNT}`**. Opening them as a different account returns a permission error (403 Forbidden).

> Write this hand-off summary in the language the user is conversing in - the wording above is the English form, not a fixed string.

💬 **Start Chatting with Your Agent (Direct Chat Link):**
👉 https://vertexaisearch.cloud.google.com/home/cid/${CONFIG_ID}/r/agent/${AGENT_ID}/session/-

💻 **Gemini Enterprise Console (Overview):**
👉 https://console.cloud.google.com/gemini-enterprise/locations/${SELECTED_LOC}/engines/${SELECTED_APP_ID}/overview/dashboard?&project=${PROJECT_ID}
*(Or fallback console if no app registered: `https://console.cloud.google.com/gemini-enterprise/overview?&project=${PROJECT_ID}`)*

📁 **Google Drive External Sample Files** (when the deploy-time upload ran):
- 👑 **Folder Owner**: `${DRIVE_OWNER_ACCOUNT}` (the account the `gdrive` CLI is signed in as)
- 🔑 **Shared With**: `${GCP_ACCOUNT}` as Writer — look under "Shared with me"
- 📂 **Open the Folder**: https://drive.google.com/drive/folders/${DRIVE_FOLDER_ID}
- 📄 Audit Report (PDF, Japanese CJK Font): ${PDF_URL}
- 📊 Supplier Ledger (Excel): ${XLSX_URL}
- 🖼️ Simulated Document 1 (JPG): ${IMG1_URL}
- 🖼️ Simulated Document 2 (JPG, Discrepancy Embedded): ${IMG2_URL}
- ❗ If `drive_upload_summary.json` carries `share_error`, print that instead of implying
  access works, and give the manual fix:
  `gdrive mutate share <FOLDER_ID> --email ${GCP_ACCOUNT} --role writer --notify=false`.

📦 **External Sample Files in Cloud Storage** (always — the staging copy is unconditional):
- 🗂️ **Browse the bucket**: https://console.cloud.google.com/storage/browser/${GCS_BUCKET_NAME}?project=${PROJECT_ID}
- 📄 **Open a file directly** (signed-in browser): one line per uploaded file,
  `https://storage.cloud.google.com/${GCS_BUCKET_NAME}/<filename>` — print the real
  filenames, never a bare `gs://` URI on its own; `gs://` is not clickable.
- 📂 Also on this machine: `./external_files/`

📁 **When the Drive upload was skipped** (no authenticated `gdrive` CLI) — say it plainly,
this is the only notice the user gets:
- ℹ️ **There is no Drive copy of these documents.** Print `skip_reason` verbatim. The
  documents themselves are complete, in Cloud Storage and `./external_files/`; only the
  Drive folder is missing, so a Drive or Sheets step in the demo script will find nothing.
- 🛠️ **To get one**: sign the `gdrive` CLI in as the account that should own the folder
  (`gdrive readonly quota --json` shows who it is now) and re-run, or upload
  `./external_files/` to a Drive folder by hand and share it with the audience. Never
  suggest asking the agent to do it — it cannot.

📊 **Firestore Data Viewer Dashboard:** 👉 ${VIEWER_URL}
🔎 **BigQuery Console:** 👉 https://console.cloud.google.com/bigquery?referrer=search&project=${PROJECT_ID}&ws=!1m4!1m3!3m2!1s${PROJECT_ID}!2s${DATASET_ID}
```

### 2. The 7 Structured Demo Prompts Playbook (Localized)

Present all 7 demo prompts formatted with Title/Persona, Category Tags, Copyable Prompt Text,
Expected Outcome, and a one-sentence **Watch Point** for the person running the demo (what to
look at on screen while this prompt runs). All 7 trace the one process instance from Phase 2,
and the last one closes with quantified outcomes — before/after cycle time, items resolved,
hand-offs completed.

Slot 5 and slot 7 carry the two autonomous delegation prompts whenever `enableManagedAgent`
is on (the default), which moves the interactive-dashboard prompt into slot 1 or 2. If the
enabled capabilities still do not fit, append up to three prompts tagged `encore` rather than
cramming two showcases into one prompt. Both rules, and the per-capability chains for
Workspace and computer use, are in `references/demo_prompts_guide.md` §5-§6.

The template below is the base progression, before those overrides:

```markdown
### 🎯 7 Structured Demo Prompts Playbook (Dynamically Localized to Target Language)

#### 1. [Role Title] Foundation & Data Overview
- **Tags**: `[Foundation]` `[Data Overview]`
- **Prompt Text**: (Generically phrased request to explore data landscape and operational KPIs in target language)
- **Expected Outcome**: Analyzes master/transaction tables and renders KPI summary in an A2UI Card.
- **Watch Point**: (What the operator should notice - e.g. the console already shows items mid-process across departments)

#### 2. [Role Title] Metadata & Knowledge Catalog Discovery
- **Tags**: `[Metadata Discovery]` `[Knowledge Catalog]`
- **Prompt Text**: (Generically phrased request inquiring about available data resources, metrics definitions, and relationships)
- **Expected Outcome**: Consults Knowledge Catalog MCP (`search_entries`, `lookup_entry`) before writing queries.
- **Watch Point**: (e.g. the agent reads the catalog before it writes a single query)

#### 3. [Role Title] Cross-Source Anomaly & Risk Detection [WOW MOMENT]
- **Tags**: `[Cross-Source WOW]` `[Drive File Binding]`
- **Prompt Text**: (Strategic inquiry about untracked discrepancies across recent deliveries/records)
- **Expected Outcome**: Autonomously cross-references Google Drive PDF/Excel against BigQuery tables, isolates the 5-15% discrepancy, and renders discrepancy cards and infographics.
- **Watch Point**: (e.g. nobody told it to open the external report - it decided to)

#### 4. [Role Title] Multi-Step Dependent Immediate Workflow [WOW MOMENT]
- **Tags**: `[Immediate Workflow WOW]` `[A2UI Batch Editor]`
- **Prompt Text**: (Request to scan unverified items, resolve mappings, and update records)
- **Expected Outcome**: Executes `SCAN -> RESOLVE -> PRESENT -> EXECUTE -> AUDIT`, presenting the (J) Dynamic Multi-Entity Batch Editor A2UI form for human confirmation before writing to DB.
- **Watch Point**: (e.g. after the approval click, the item moves to the next department on the operations console)

#### 5. [Role Title] Large-Scope Batch / Background Reconciliation [WOW MOMENT]
- **Tags**: `[Background Workflow WOW]` `[Execution Mode Dialog]`
- **Prompt Text**: (Comprehensive quarterly reconciliation request across all historical records)
- **Expected Outcome**: Recognizes large batch scope and presents Execution Mode Dialog (Immediate vs Background vs Scheduled), kicking `/execute_task` when background mode is selected.
- **Watch Point**: (e.g. the agent proposes background mode on its own, then keeps the chat usable while it runs)

#### 6. [Role Title] Scheduled Automated Monitoring Setup
- **Tags**: `[Scheduled Monitoring]` `[Pub/Sub Task]`
- **Prompt Text**: (Request to set up automated recurring threshold monitoring every morning at 09:00 AM)
- **Expected Outcome**: Explains monitoring logic, registers recurring cron schedule with Pub/Sub.
- **Watch Point**: (e.g. the schedule it proposes matches the department's own escalation rule)

#### 7. [Role Title] End-to-End Strategic Automation
- **Tags**: `[Strategic Automation]` `[End-to-End]`
- **Prompt Text**: (Comprehensive executive request combining cross-source analytics, workflow execution, notification drafting, and audit logging)
- **Expected Outcome**: Synthesizes all data sources, produces executive summary infographic, updates records, and logs audit trail.
- **Watch Point**: (e.g. the closing summary states the before/after cycle time for the instance the whole demo followed)
```

---

## Phase 8: Cleanup & Teardown (On-Demand)

When the demo is concluded, delete all provisioned resources (including the Agent Engine
Sandbox and the Managed Autonomous Agent):
```bash
bash scripts/cleanup.sh
```

Read the per-resource lines, not the closing banner. Every job runs under `|| true` so that one
failure cannot strand the rest, which means the script finishes whatever happened: `✅` deleted,
`⚠️` already gone or skipped, `❌` still there. A `❌`, or a `⚠️` for something you know existed,
needs a manual delete — an Agent Engine, a bucket or a Firestore collection left behind keeps
billing. Run it from the demo directory so it picks up `.env`; without `DOMAIN_SLUG`/`SUFFIX` it
cannot name the two GCS buckets and says so rather than guessing.

---

## References & Templates

- For Discovery Engine DataStore Connectors & Search: read `references/datastore_connectors.md`.
- For Deployment sequence, Dependency graph & the full `.env` key reference: read `references/deployment_and_iam.md`.
- For External sample files & Google Drive upload: read `references/external_files_and_drive.md`.
- For 7 Demo prompts specification: read `references/demo_prompts_guide.md`.
- For Multi-Agent routing & Sandbox code execution: read `references/multi_agent_architecture.md`.
- For MCP server integrations & Workspace Auth: read `references/mcp_catalog.md`.
- For Data generation & Knowledge Catalog metadata: read `references/data_generation.md`.
- For A2UI JSON payload format & system instructions: read `references/a2ui_catalog.md`.
