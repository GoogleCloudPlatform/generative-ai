# Discovery Engine DataStore Connectors Reference Guide

> **Purpose**: Technical architecture, API specifications, and operational patterns for provisioning, binding, querying, and cleaning up Discovery Engine (Gemini Enterprise) DataStore connectors.

---

## 1. Architecture: MCP mode vs. RAG-preferred mode

`DATA_EXPLORATION_MODE` picks one of two modes. **`mcp` is the default**; `rag` is the
opt-in that provisions everything the rest of this document describes.

### Why `mcp` is the default

The four-to-five model round trips an index was meant to remove were never the SQL. They were
the *metadata expedition in front of it* — `search_entries` → `lookup_entry` →
`get_table_info` → `execute_sql` — which the generic METADATA-FIRST rule demands of an agent
that was handed no schema. This generator hands the agent a full data-asset catalog inside its
system instruction, so `agent.py`'s mcp routing block overrides that rule and a figure question
becomes **one** `execute_sql` call. That is the same latency the index was bought for, with no
Discovery Engine to create, import, scope or clean up, and nothing attached to a Gemini
Enterprise app that other demos share.

Prior to v11.73 the hybrid variant of `rag` was the default, on the belief that the round trips
were unavoidable without an index. They were not; they were an instruction problem.

### When to choose `rag`

When the demo turns on **documents** rather than on numbers — manuals, reports, contracts,
scanned receipts. Semantic retrieval over unstructured text with chunk-level citations is
something SQL genuinely cannot do, and that is the case the index earns its provisioning cost
in. A demo whose questions are all aggregates and comparisons gains nothing from it.

### Routing rule in `rag` mode (enforced in `agent.py`, appended to the instruction at runtime)

| Question shape | Path |
| :--- | :--- |
| Lookup by name / id / keyword, "what do we have on X", find the manual or report covering Y, the opening exploratory question | **Search** — `search_datastore` |
| Aggregate over many rows, join across tables, filter over a numeric or date range | **SQL** — `execute_sql` |
| Any figure stated as fact, placed in a card, or used in a calculation | **SQL**, always |
| Any write (INSERT / UPDATE / DELETE / MERGE, Firestore) | **SQL / MCP**, always |

The last two rows are what make the read path safe. The index lags the tables — a row written a
minute ago may not be indexed yet — so search is allowed to find *what* to compute on but never
to supply the number itself. On a miss the agent falls back to SQL silently; the user is never
told which path ran.

`rag` mode additionally requires the wiring to exist: the block is gated on
`GEMINI_ENTERPRISE_APP_ID` / `DEFAULT_DATASTORE_ID` as well as on the mode, and
`search_datastore` is not even registered as a tool otherwise. The mode says what was requested;
those say what the deploy managed to wire, and pointing the model at an unbacked
`search_datastore` trades a slow answer for a failed one. A `rag` deploy that found no Gemini
Enterprise app therefore degrades to the mcp block rather than to nothing.

| Dimension | `mcp` (**Default**) | `rag` |
| :--- | :--- | :--- |
| **Primary Mechanism** | Python MCP Toolsets (`bigquery_toolset`, `firestore`, `gcs`) + the catalog in the system instruction | DataStore Search (RAG) for reads + MCP Actions (CRUD/SQL) for figures and writes |
| **Data Types** | Structured relational tables, key-value documents | All types (Unstructured docs + Structured DBs) |
| **Search Capabilities** | Deterministic SQL filters, exact aggregations, joins | Semantic discovery + exact calculations |
| **Update / Mutations** | Real-time `UPDATE`, `INSERT`, batch edits, A2UI action commits | Identical — writes never use the index |
| **Grounding & Citations** | Explicit SQL row data | Native document chunk citations with URIs and page numbers, plus live database verification |
| **Provisioning cost** | None | DataStore creation + import, engine binding, scope wiring, and teardown |

---

## 2. Supported DataStore Connector Types

### 2.1 Google Cloud Storage (GCS) DataStore
- **Source**: `gs://${GCS_BUCKET_NAME}/*`
- **Content Type**: `CONTENT_REQUIRED` (Unstructured)
- **Supported Formats**: PDF (with CJK Japanese OCR support), Excel (`.xlsx`), Word (`.docx`), HTML, TXT, images.
- **Use Case**: Regulatory manuals, inspection reports, contracts, scanned delivery receipts, supplier catalogs.

### 2.2 BigQuery DataStore
- **Source**: `${PROJECT_ID}.${DATASET_ID}.${TABLE_NAME}`
- **Content Type**: `STRUCTURED` / `NO_CONTENT` (Custom Schema)
- **Indexing Options**: Searchable text fields + filterable metadata fields (dates, categories, status).
- **Use Case**: Natural language exploration across large transaction logs, CRM records, inventory catalogs without manual SQL authoring.

### 2.3 Google Drive DataStore
- **Source**: Google Workspace Drive Folders / Shared Drives
- **Content Type**: Google Docs, Sheets, Slides, Drive PDFs.
- **Use Case**: Cross-referencing enterprise Drive documents directly within Gemini Enterprise.

### 2.4 Firestore DataStore
- **Source**: Firestore Collection JSONL exports or real-time sync.
- **Content Type**: Operational task records, incident logs, workflow state.

---

## 3. Discovery Engine API Specifications

### 3.1 Create DataStore
- **Endpoint**: `POST https://${ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores?dataStoreId=${DATASTORE_ID}`
- **Headers**:
  ```http
  Authorization: Bearer ${TOKEN}
  Content-Type: application/json
  X-Goog-User-Project: ${PROJECT_ID}
  ```
- **Payload (GCS Unstructured)**:
  ```json
  {
    "displayName": "Demo GCS Documents (${SERVICE_NAME})",
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    "contentConfig": "CONTENT_REQUIRED",
    "documentProcessingConfig": {
      "defaultParsingConfig": {
        "digitalParsingConfig": {}
      }
    }
  }
  ```
- **Payload (BigQuery Structured)**:
  ```json
  {
    "displayName": "Demo BigQuery Tables (${SERVICE_NAME})",
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    "contentConfig": "NO_CONTENT"
  }
  ```

### 3.2 Import Documents / Data
- **Endpoint**: `POST https://${ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATASTORE_ID}/branches/0/documents:import`
- **Payload (GCS Source)**:
  ```json
  {
    "gcsSource": {
      "inputUris": ["gs://${GCS_BUCKET_NAME}/*"],
      "dataSchema": "unstructured"
    },
    "reconciliationMode": "FULL"
  }
  ```
- **Payload (BigQuery Source)**:
  ```json
  {
    "bigquerySource": {
      "projectId": "${PROJECT_ID}",
      "datasetId": "${DATASET_ID}",
      "tableId": "${TABLE_NAME}",
      "dataSchema": "custom"
    },
    "reconciliationMode": "INCREMENTAL"
  }
  ```

### 3.3 Attach DataStore to Gemini Enterprise Engine (App)
- **Endpoint**: `POST https://${ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/engines/${APP_ID}/dataStores`
- **Payload**:
  ```json
  {
    "dataStoreId": "${DATASTORE_ID}"
  }
  ```

### 3.4 Search DataStore (Agent Tool Execution)
- **Endpoint**: `POST https://${ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATASTORE_ID}/servingConfigs/default_search:search`
- **Payload**:
  ```json
  {
    "query": "<natural-language question in the demo's own language>",
    "pageSize": 5,
    "contentSearchSpec": {
      "snippetSpec": {
        "returnSnippet": true
      },
      "extractiveContentSpec": {
        "maxExtractiveAnswerCount": 1,
        "maxExtractiveSegmentCount": 3
      }
    }
  }
  ```

---

## 4. Teardown & Cleanup Dependency Sequence

To prevent `FAILED_PRECONDITION: DataStore is attached to Engine` errors, cleanup MUST proceed in this exact order:

1. **Detach DataStore from Engine**:
   `DELETE https://${ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/engines/${APP_ID}/dataStores/${DATASTORE_ID}`
2. **Delete DataStore Resource**:
   `DELETE https://${ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATASTORE_ID}`
3. **Delete Underlying Storage & Compute** (Cloud Run, BQ, GCS, Firestore, Pub/Sub).
