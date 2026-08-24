# External Sample Files Generation & Google Drive Storage

The GE Demo Generator synthesizes realistic external sample data files (PDF Reports, Excel Ledgers, Simulated Operational Scans) that live OUTSIDE the demo database, so the agent has something to reconcile against. This enables cross-source reasoning demos, document OCR/scanning workflows, and direct Google Workspace MCP exploration.

Where those files end up is the part that surprises people, so it is stated up front:
they are always written locally and staged to `gs://$GCS_BUCKET_NAME/`; the deploy-time
`gdrive` upload puts them in the **operator's** Drive and shares that folder with the
deploy target as Writer (§5); and when there is no such folder, the target gets its own
copy at conversation time through `import_demo_files_to_my_drive`, which runs with that
user's OAuth token — by itself on the user's first message, and on request afterwards
(§5.3). A deployment cannot write into someone else's Drive on its own; sharing is how
the deploy-time folder reaches the target.

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
4. Those two prompts only find something the user's Drive can see. The deploy-time upload
   covers that by sharing its folder with the deploy target (§5), which makes the files
   searchable for that account. When there was no deploy-time upload at all, the agent
   imports the files on the user's first message all by itself
   (`import_demo_files_to_my_drive`, §5.3), so the ledger is a real Google Sheet by the
   time the Sheets prompt runs. The user can also ask — "import the demo's sample
   documents into my Google Drive" — and that works in either case, which is how a
   participant who is not the deploy target gets a copy of their own.

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
   must not hold the assets at all; the agent-side import (§5.3) then covers Drive.

4. **When the upload is skipped**, nothing is lost: the files are in `./external_files`
   and in `gs://$GCS_BUCKET_NAME/`, which `setup_and_deploy.sh` now stages in **every**
   mode (before v2.9.0 the copy sat inside the rag branch, so an MCP-mode demo had no
   bucket at all). `setup_and_deploy.sh` reads `upload_skipped_reason` from
   `external_files/drive_upload_summary.json` and prints the reason plus both paths in
   the final banner.

   **The files still get into the target's own Drive at conversation time, and the user
   does not have to ask.** With `enableWorkspaceAuth` (or full MCP),
   `import_demo_files_to_my_drive` lists `gs://$GCS_BUCKET_NAME/`, creates a folder
   `GE Demo Sample Files - <DEMO_ID>` and uploads each document with the **signed-in
   user's** OAuth token, so that user OWNS the result — no "Shared with me", no
   cross-tenant surprise. The `.xlsx` is import-converted to a Google Sheet, the PDF and
   the scans keep their format.

   **Automatic import (v2.10.0).** Nobody opening a demo for the first time knows the
   sentence "import the demo's sample documents into my Google Drive" exists, so the same
   import also runs on its own. `root_agent`'s before-agent callback calls
   `tools.maybe_auto_import_demo_files()` on the first turn of a conversation; the work
   happens on a worker thread and the turn waits `AUTO_IMPORT_WAIT_S` (default 8s) for it,
   so the links normally arrive in the very first reply. When the upload takes longer the
   worker parks the announcement and the next turn delivers it. Either way it is announced
   through `{_bg_task_results}` — the same channel background tasks use — with an
   instruction to reproduce the links and say it once, in the user's language.

   | Question | Answer |
   | --- | --- |
   | How is a second copy avoided? | A Firestore marker `<DEMO_ID>_drive_imports/<email>`. It is keyed on the **Drive account the token belongs to** (from `tokeninfo`), never on the ADK `user_id`, which GE mints per session — that key would hand the same person a new folder in every conversation. The marker also survives an instance restart, so two Cloud Run instances cannot both import. |
   | What if the user deletes the folder? | The recorded folder id is checked with a `files.get` before its links are handed out again; a trashed or missing folder re-imports. A network error during that check counts as "still there", not as deletion. |
   | What about two instances at once? | The claim is written with Firestore `create()`, which refuses a document that already exists, so the loser backs off with `in_progress` instead of importing a second folder. |
   | What if a claim crashes mid-upload? | The `running` marker is taken over after 10 minutes. A failed import deletes its own claim. |
   | Can the user still ask? | Yes, and it is the same code path. The tool returns the recorded folder (`already_imported`) instead of a second copy, or `in_progress` while the automatic import is still uploading. |
   | What if the deploy already uploaded to Drive? | Then the unprompted run stands down. `setup_and_deploy.sh` passes the shared folder as `DRIVE_FOLDER_URL`, and its presence suppresses the automatic import — a second copy of documents the user can already open is noise. Asking still imports a personal copy, and the answer names the shared folder too (`shared_folder_from_deploy`). |
   | How is it switched off? | `AUTO_IMPORT_DEMO_FILES=0` on the Cloud Run service. The tool stays; only the unprompted run stops. |

   Constraints, all structural:

   | Constraint | Why |
   | --- | --- |
   | Live user turn only | The OAuth token is captured per request and has no refresh path; `user_id == "background-worker"` is refused outright, in the tool and in the automatic path. |
   | Needs `enableWorkspaceAuth` or `enableWorkspaceMcp` | Without the GE authorization no user token ever arrives; the tool answers `disabled` and the automatic import returns nothing. |
   | `GCS_BUCKET_NAME` must reach Cloud Run | It is in `CR_ENV_VARS`; without it the tool answers `error` / not configured and the automatic import does not start. |
   | Announcement is in-process | The parked announcement lives in the instance that ran the import. If that instance is recycled before the next turn, the files are still in Drive but nobody says so — the user gets the links by asking. |

   `auth_required` means the user has not consented yet (or the token expired): the fix
   is for the user to re-authorize the agent in Gemini Enterprise, not to re-deploy. The
   automatic import treats a missing token the same way, silently: it does not consume
   the one-shot trigger, so the turn after consent tries again.

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

