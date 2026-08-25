# External Sample Files Generation & Google Drive Storage

The GE Demo Generator synthesizes realistic external sample data files (PDF Reports, Excel Ledgers, Simulated Operational Scans) that live OUTSIDE the demo database, so the agent has something to reconcile against. This enables cross-source reasoning demos, document OCR/scanning workflows, and direct Google Workspace MCP exploration.

Where those files end up is the part that surprises people, so it is stated up front:
they are always written locally and staged to `gs://$GCS_BUCKET_NAME/`; the deploy-time
`gdrive` upload puts them in the **operator's** Drive and shares that folder with the
deploy target as Writer (§5). That upload is the **only** path into a Drive. When it does
not run — no CLI, no CLI identity, or `SKIP_HOST_DRIVE_UPLOAD=1` — there is no Drive copy
of these documents at all, and the deploy completion banner says so with the reason (§5.4).
The deployed agent cannot make one: a deployment cannot write into someone else's Drive on
its own, and sharing is how the deploy-time folder reaches the target.

---

## 1. Generated External File Types & Specifications

| File Type | Format / Extension | Specification & Realism Requirements | Role in Demo |
|---|---|---|---|
| **Audit / Reconciliation Report** | PDF (`.pdf`) | Multi-section business report (at least 1,500 chars) with Executive Summary, Background, Table Data, Chart placeholders / graphs, and specific transaction IDs. | Seeds 5-20% intentional discrepancies against BigQuery tables to trigger **Prompt 3 (Cross-Source WOW Moment)**. |
| **Operational Supplier Ledger** | Excel (`.xlsx`) | Composite workbook with Report Title, KPI summary cards, and 40-80 detailed transaction rows with units, currency formatting, and FK references (70%+ ID match). | Enables high-volume cross-referencing and JOIN-based reconciliation against BigQuery data. |
| **Simulated Operational Documents** | JPEG (`.jpg`) | Scanned purchase order sheets or delivery slips generated with `gemini-3.1-flash-image` featuring realistic handwritten ink annotations, company stamps, headers, and line items. | Triggers OCR / Multimodal extraction and **(J) Dynamic Multi-Entity Batch Editor** workflows. |

---

## 2. Cross-Source Binding & Anomaly Seeding Strategy

To ensure impressive demonstration moments ("WOW Moments"):
1. **Logical Key Symmetry**: The primary keys (e.g. `order_id`, `lot_id`, `invoice_id`) cited in the external PDF and Excel files MUST actually exist in the BigQuery tables.
2. **Intentional Variance (Audit Discrepancy)**: 2-4 specific records in the external files have slightly different values (e.g. quantity received = 1,050 vs system expected = 1,200) or status deviations.
3. **Autonomous Cross-Referencing**: When given a high-level strategic question (Prompt 3), the agent autonomously discovers this anomaly by querying internal tables and comparing them with the external Drive file.

---

## 3. Google Drive Folder Creation & Upload Flow

During Phase 3, the generator executes:

```bash
# 1. Generate PDF and Excel files locally
uv run --with "openpyxl,reportlab,pillow" python3 scripts/generate_and_upload_external_files.py \
  --domain "$DOMAIN" \
  --company "$COMPANY_NAME" \
  --suffix "$SUFFIX" \
  --outdir "./external_files" \
  --spec-file "./data/external_files_spec.json"

# --spec-file holds this demo's own content and is required for a realistic demo:
# {
#   "style":  {"handwriting_language": "...", "routine_doc_kind": "...",
#              "exception_doc_kind": "...", "location": "...",
#              "approval_seal": "...", "review_stamp": "...", "urgent_note": "..."},
#   "pdf":    {"title": "...", "sections": [{"heading": "...", "content": "..."}],
#              "discrepancy": {"heading": "...", "table_data": [[...], ...]}},
#   "excel":  {"title": "...", "kpis": [{"label": "...", "value": "..."}],
#              "headers": [...], "rows": [[...], ...]},
#   "scans":  [{"title": "...", "doc_no": "...", "date": "...", "headers": [...],
#               "rows": [[...], ...], "is_discrepancy": false}, {...}]
# }
# Everything above is written in the demo's language and domain. The script itself
# ships only generic placeholders - never bake a customer's content into it.

# 2. Uploaded to Google Drive via gdrive CLI:
# Folder: "GE Demo - <Company Name> (<Suffix>)"
# Files:
#   - <domain>_audit_report.pdf  -> https://drive.google.com/file/d/<PDF_ID>/view
#   - <domain>_external_ledger.xlsx -> https://drive.google.com/file/d/<XLSX_ID>/view
#   - handwritten_order_1.jpg   -> https://drive.google.com/file/d/<IMG1_ID>/view
#   - handwritten_order_2.jpg   -> https://drive.google.com/file/d/<IMG2_ID>/view
```

---

## 4. Google Workspace MCP Integration

When `enableWorkspaceMcp: true` is configured (step 1 applies to `enableWorkspaceAuth` alone as well):
1. The agent is registered in Gemini Enterprise with `--authorization-id`.
2. The agent has direct access to `Google Drive MCP` and `Google Sheets MCP`.
3. The agent can directly search the user's Drive folder for these files:
   - "Search Google Drive for the latest supplier audit report"
   - "Read the reconciliation ledger from Google Sheets and compare with operational tables"
4. Those two prompts only find something the user's Drive can see, so they depend on the
   deploy-time upload having run and its share having landed on the account driving the
   demo (§5). When it did not, those two prompts come back empty and nothing recovers
   later: check the completion banner before promising a Drive step, and give the
   audience the Cloud Storage links instead. The agent is told the same thing, so it
   answers "the documents are in cloud storage" rather than offering an import it cannot
   perform.

---

## 5. Account Ownership, Permissions & Multi-Account Access Guidance

**Two different identities are in play, and they are often not the same account.**
The *deploy target* is `gcloud config get-value account` — the account that owns the
project and will run the demo. The *upload identity* is whoever the `gdrive` CLI is
authenticated as, which is the operator running this skill. The CLI can only create
files in its own Drive, so the folder belongs to the operator and the target reaches it
through a share.

1. **Upload, then share.** `generate_and_upload_external_files.py` resolves the CLI
   identity with `gdrive readonly quota --json` (falling back to an email match on the
   plain output), uploads into that Drive, and — when the deploy target is a different
   account — runs `gdrive mutate share --email <target> --role writer --notify=false`
   on the folder:

   | Situation | Behaviour |
   | --- | --- |
   | CLI identity == deploy target | Upload to Drive, folder owned by the target. No share needed. |
   | CLI identity != deploy target | Upload to the operator's Drive, **share the folder with the target as Writer**. It appears under the target's "Shared with me". |
   | CLI identity undeterminable | Skip the upload — there is no Drive to write into. |
   | `gdrive` CLI absent | Skip the upload. |

   v2.9.0 required the two identities to match and skipped otherwise, which in practice
   meant most demos got no Drive folder at all. Sharing gives the target working links
   without the operator having to switch accounts, so it is now the default.

2. **The share can fail, and that is reported, not swallowed.** Cross-domain sharing is
   a Workspace policy decision (`google.com` → a customer domain is frequently blocked).
   The script records the failure as `share_error` in
   `external_files/drive_upload_summary.json`; `setup_and_deploy.sh` prints a
   `❗ SHARING FAILED` block with the reason and the manual `gdrive mutate share`
   command. Never print a folder link as if it worked when the share did not — the
   target opens it and gets 403/404.

3. **Opt-out**: `SKIP_HOST_DRIVE_UPLOAD=1` restores the old behaviour — skip the upload
   whenever the CLI identity is not the deploy target. Use it when the operator's Drive
   must not hold the assets at all, and accept that the demo then has no Drive copy: this
   is a trade, not a fallback.

4. **When the upload is skipped, the documents are intact but there is no Drive folder.**
   They are in `./external_files` and in `gs://$GCS_BUCKET_NAME/`, which
   `setup_and_deploy.sh` stages in **every** mode (before v2.9.0 the copy sat inside the
   rag branch, so an MCP-mode demo had no bucket at all). `setup_and_deploy.sh` reads
   `upload_skipped_reason` from `external_files/drive_upload_summary.json` and prints it,
   under a `📁 External Sample Files - NOT in Google Drive` heading, with what it costs (a
   Drive or Sheets step in the demo script finds nothing) and how to fix it (sign the
   `gdrive` CLI in and re-run, or upload `./external_files/` by hand and share it).

   **This banner is the whole recovery story, by design.** v2.10.0 tried to close the gap
   from the other end: the agent copied the documents into the signed-in user's Drive with
   their OAuth token, unprompted, on the first turn of every conversation, behind a
   Firestore claim, a worker thread and a wait budget. v2.11.0 deleted all of it — the
   tool, the automatic run, the claim, `AUTO_IMPORT_DEMO_FILES` and `DRIVE_FOLDER_URL`.
   Three reasons, in order of weight:

   | Why it went | Detail |
   | --- | --- |
   | It uploaded the wrong things | The uploader took every object at the root of `gs://$GCS_BUCKET_NAME/`. In rag mode that root is also the datastore's corpus, so on a real demo it was 13 objects / 103 MB of the customer's own manuals, not the 4 generated samples — into an end user's personal Drive, without anyone asking for it. |
   | The machinery outweighed the feature | Idempotency across instances and conversations needed a Firestore claim keyed on the token's email, a takeover timeout, a trashed-folder re-check and a parked announcement channel; roughly 390 lines to deliver something the deploy already does in one `gdrive` call. |
   | It paid for itself on every turn | The before-agent callback ran on all turns, and the first one blocked up to `AUTO_IMPORT_WAIT_S` (8s) waiting for the copy — a budget sized for 4 small files. |

   The agent's system instruction now states the same thing the banner does: the documents
   live in cloud storage, the deploy shares the Drive folder, and if a Drive search comes
   back empty it must say so rather than offer a copy it cannot make.

5. **Reporting & Access Instructions.** Every path to the files ends in a link the
   reader can click; a bare `gs://` URI or a folder name is not a link.

   Drive (only when the upload actually ran):
   - 👑 **Drive Owner**: the account that owns the folder
   - 🔑 **Shared with**: the deploy target, as Writer
   - 📂 **Open the folder**: `https://drive.google.com/drive/folders/<FOLDER_ID>`
   - 📄 Per-file links: `https://drive.google.com/file/d/<FILE_ID>/view`
   - ⚠️ **Multi-Account Browser Warning**:
     "Make sure to switch your browser to the owner Google Account before opening the
     Google Drive links. If you are signed into multiple Google accounts, accessing the
     link with a non-owner account will fail with Permission Denied (403/404)."
   - If owner != target, say so explicitly: the folder appears under "Shared with me"
     for the target, and the target cannot move it into its own My Drive.

   Cloud Storage (always, since the staging copy always happens):
   - 🗂️ **Browse the bucket**:
     `https://console.cloud.google.com/storage/browser/<BUCKET>?project=<PROJECT_ID>`
   - 📄 **Open a file**: `https://storage.cloud.google.com/<BUCKET>/<OBJECT>` — this
     serves the object to a signed-in browser with `storage.objects.get`, so it is the
     one to print for each uploaded file. The console URL is the fallback when the
     object names are not known at report time.

