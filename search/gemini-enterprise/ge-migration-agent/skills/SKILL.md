---
name: migration-config-skill
description: Holds canonical source and target environment parameters and verified DataStore mappings.
metadata:
  environments:
    source:
      project_number: "404109417257"
      project_id: learn-w-me
      region: global
      engine_id: enterprise-search-17416389_1741638989378
    target:
      project_number: "1087766539550"
      project_id: "acxiom-425322"
      region: global
      engine_id: gemini-enterprise-17811872_1781187299515
  datastores_mapping:
    ge-drive-all_1776953145638_google_drive: ge-drive-all_1781187446457_google_drive
    
  connectors_mapping:
    ge-drive-all: Drive
    GeGmail: geGmail
    googleSearch: googleSearch
    urlContext: urlContext
---

# ADK Administration Setup & Migration Instructions

This file serves as the single source of truth for Gemini Enterprise migrations. Administrators can fully configure source-to-target resource pairings by updating the YAML metadata frontmatter above.

---

## Administrative Setup Guide

### 1. Environments Configuration
Set your official canonical source and target project definitions under `environments`:
- **`project_number`**: The numeric Google Cloud Project Number (e.g., `404109417257`).
- **`engine_id`**: The fully qualified Discovery Engine app/engine ID.

### 2. DataStore Grounding Mappings (`datastores_mapping`)
Map underlying knowledge search collections and grounding data stores (assigned under `dataStoreSpecs`) using their exact resource ID suffix:
```yaml
datastores_mapping:
  # Source ID -> Target ID
  snowflake-mcp-may29_1780067471814_mcp_data: snowflake-mcp-may29_1780829795319_mcp_data
  ge-drive-all_1776953145638_google_drive: ge-drive-all_1780835769760_google_drive
```
*Note: Always use the fully qualified ID suffix (e.g., `_google_drive`, `_mcp_data`) to prevent substring truncation.*

### 3. Visual Connector & Tool Mappings (`connectors_mapping`)
Map display aliases and frontend extension tool chips (assigned under `selectedTools`) to ensure visual rendering parity in the Agent Designer UI canvas:
```yaml
connectors_mapping:
  # Source UI Badge -> Canonical Target UI Token
  Snowflake Mcp May29: custom_mcp
  ge-drive-all: Drive
```

---

## Operational Execution

Once configured, run live migrations or offline GCS imports directly:

```bash
# 1. Execute live cross-environment migration
uv run ./migrate.py migrate-agent "Quarterly Business Review Generator" --force

# 2. Import agent definition from GCS offline backup
uv run ./migrate.py import-agent-gcs quarterly_business_review_export.json --target-engine <TARGET_ENGINE_ID>
```
