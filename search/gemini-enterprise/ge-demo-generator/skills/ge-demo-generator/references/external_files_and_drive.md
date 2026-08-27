# External Sample Files Generation & Google Drive Storage

The GE Demo Generator synthesizes realistic external sample data files (PDF Reports, Excel Ledgers, Simulated Operational Scans) that live OUTSIDE the demo database, so the agent has something to reconcile against. This enables cross-source reasoning demos, document OCR/scanning workflows, and direct Google Workspace MCP exploration.

Where those files end up is the part that surprises people, so it is stated up front:
they are always written locally and staged to `gs://$GCS_BUCKET_NAME/`; the deploy-time
upload then puts them in the Drive of **the account running the deploy**, using the
Drive v3 REST API with that machine's own `gcloud` access token (§5). That upload is the
**only** path into a Drive. When it does not run — no Drive scope on the token, or
`SKIP_DRIVE_UPLOAD=1` — there is no Drive copy of these documents at all, and the deploy
completion banner says so with the reason and with the one command that fixes it (§5.4).
The deployed agent cannot make one: a deployment cannot write into someone else's Drive.

Nor is there an index-side route to the same documents: a Google Drive data store is created
by Discovery Engine but cannot be read by the agent's service account, and cannot be scoped to
a folder. See `references/datastore_connectors.md` §2.3 for the live evidence.

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

# 2. Uploaded to Google Drive via the Drive v3 REST API, authenticated with
#    `gcloud auth print-access-token` - no CLI to install, and the folder is
#    owned by the account running the deploy. Re-running the deploy reuses the
#    folder of the same name instead of creating a second one.
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
4. Those two prompts only find something the *signed-in user's* Drive can see, so they
   depend on the deploy-time upload having run, and on the demo being driven by the
   account that ran the deploy (§5). When either is untrue, those two prompts come back
   empty and nothing recovers later: check the completion banner before promising a Drive
   step, and give the audience the Cloud Storage links instead. The agent is told the same
   thing, so it answers "the documents are in cloud storage" rather than offering an
   import it cannot perform.

---

## 5. Account Ownership, Permissions & Multi-Account Access Guidance

**One identity is in play: the account `gcloud` is logged in as.** It owns the project,
it runs the deploy, and — since v2.13.0 — it owns the Drive folder, because the upload is
a Drive v3 REST call carrying that account's own access token. There is no second CLI, no
second Drive, and nothing to share with the deploy target, because the deploy target *is*
the owner.

1. **The prerequisite is the Drive scope, and it is the only thing that usually fails.**
   A plain `gcloud auth login` grants `cloud-platform` and nothing else, so Drive answers
   `403 ACCESS_TOKEN_SCOPE_INSUFFICIENT`. `generate_and_upload_external_files.py` probes
   `GET drive/v3/about?fields=user` first, which resolves the identity and the scope in
   one call, and turns that 403 into the fix:

   ```
   gcloud auth login --enable-gdrive-access
   ```

   | Situation | Behaviour |
   | --- | --- |
   | Token has the Drive scope | Create/reuse `GE Demo - <Company> (<Suffix>)`, upload the four documents, folder **owned by the deploy account**. |
   | Token has no Drive scope, or no token at all | Skip the upload; the banner prints the re-login command above. |
   | `SKIP_DRIVE_UPLOAD=1` | Skip the upload deliberately. |

   Until v2.11.x this used an internal `gdrive` CLI authenticated as the operator, so the
   folder was the operator's and the deploy target reached it through a share. Two
   reasons that went: the binary is Google-internal and cannot ship in the public copy of
   this skill, and a `google.com` → customer-domain share is frequently refused by
   policy, which handed the target a link that 404s. Owning the folder removes both.

2. **The upload is idempotent by name, folder and file both.** `files.list` with
   `name = '<folder>' and mimeType = folder and trashed = false and 'me' in owners`
   runs before `files.create`, so re-running the deploy reuses the folder it already made
   rather than leaving three of them. `'me' in owners` is not decoration: without it a
   same-named folder someone else shared with you wins the lookup, and the documents land
   in a stranger's Drive. Each document then does the same lookup inside that folder
   (`name = '<file>' and '<folder id>' in parents and trashed = false`) and, if it is
   already there, is uploaded as `PATCH .../files/<id>?uploadType=multipart` instead of a
   second `POST`. Verified against the live API: two consecutive runs leave 4 files, not
   8, with the same file ids and a bumped `version`. Keeping the ids matters because a
   link pasted into a demo script survives the re-deploy. (`parents` is only writable on
   create, so the update sends the name alone.)

3. **Link sharing is best-effort and never blocks.** After the folder exists the script
   asks for `{"type": "anyone", "role": "reader"}` so the audience can open the links
   without being added one by one. Plenty of organizations forbid that; the refusal is
   recorded as `share_error` in `external_files/drive_upload_summary.json` and the banner
   prints an `ℹ️ LINK SHARING OFF` note. This is a convenience that did not land, not the
   old broken state — the owner can always open the folder, so the demo still works.

4. **Opt-out**: `SKIP_DRIVE_UPLOAD=1` skips Drive entirely, for a machine whose Drive must
   not hold the assets. Accept that the demo then has no Drive copy: this is a trade, not
   a fallback. (It replaces `SKIP_HOST_DRIVE_UPLOAD`, which was about a *second* identity
   that no longer exists.)

5. **When the upload is skipped, the documents are intact but there is no Drive folder.**
   They are in `./external_files` and in `gs://$GCS_BUCKET_NAME/`, which
   `setup_and_deploy.sh` stages in **every** mode (before v2.9.0 the copy sat inside the
   rag branch, so an MCP-mode demo had no bucket at all). `setup_and_deploy.sh` reads
   `upload_skipped_reason` from `external_files/drive_upload_summary.json` and prints it,
   under a `📁 External Sample Files - NOT in Google Drive` heading, with what it costs (a
   Drive or Sheets step in the demo script finds nothing) and how to fix it
   (`gcloud auth login --enable-gdrive-access` and re-run, or upload `./external_files/`
   by hand and share it).

   **This banner is the whole recovery story, by design.** v2.10.0 tried to close the gap
   from the other end: the agent copied the documents into the signed-in user's Drive with
   their OAuth token, unprompted, on the first turn of every conversation, behind a
   Firestore claim, a worker thread and a wait budget. v2.11.0 deleted all of it — the
   tool, the automatic run, the claim, `AUTO_IMPORT_DEMO_FILES` and `DRIVE_FOLDER_URL`.
   Three reasons, in order of weight:

   | Why it went | Detail |
   | --- | --- |
   | It uploaded the wrong things | The uploader took every object at the root of `gs://$GCS_BUCKET_NAME/`. In rag mode that root is also the datastore's corpus, so on a real demo it was 13 objects / 103 MB of the customer's own manuals, not the 4 generated samples — into an end user's personal Drive, without anyone asking for it. |
   | The machinery outweighed the feature | Idempotency across instances and conversations needed a Firestore claim keyed on the token's email, a takeover timeout, a trashed-folder re-check and a parked announcement channel; roughly 390 lines to deliver something the deploy already does in a handful of REST calls. |
   | It paid for itself on every turn | The before-agent callback ran on all turns, and the first one blocked up to `AUTO_IMPORT_WAIT_S` (8s) waiting for the copy — a budget sized for 4 small files. |

   The agent's system instruction now states the same thing the banner does: the documents
   live in cloud storage, the deploy puts a copy in the deploying account's Drive, and if a
   Drive search comes back empty it must say so rather than offer a copy it cannot make.

6. **Reporting & Access Instructions.** Every path to the files ends in a link the
   reader can click; a bare `gs://` URI or a folder name is not a link.

   Drive (only when the upload actually ran):
   - 👑 **Drive Owner**: the account that ran the deploy
   - 🔑 **Link sharing**: "Anyone with link (Reader)" when the org allows it; otherwise
     the `ℹ️ LINK SHARING OFF` note, and the audience needs an explicit share
   - 📂 **Open the folder**: `https://drive.google.com/drive/folders/<FOLDER_ID>`
   - 📄 Per-file links: `https://drive.google.com/file/d/<FILE_ID>/view`
   - ⚠️ **Multi-Account Browser Warning**:
     "Make sure to switch your browser to the owner Google Account before opening the
     Google Drive links. If you are signed into multiple Google accounts, accessing the
     link with a non-owner account will fail with Permission Denied (403/404)."

   Cloud Storage (always, since the staging copy always happens):
   - 🗂️ **Browse the bucket**:
     `https://console.cloud.google.com/storage/browser/<BUCKET>?project=<PROJECT_ID>`
   - 📄 **Open a file**: `https://storage.cloud.google.com/<BUCKET>/<OBJECT>` — this
     serves the object to a signed-in browser with `storage.objects.get`, so it is the
     one to print for each uploaded file. The console URL is the fallback when the
     object names are not known at report time.

