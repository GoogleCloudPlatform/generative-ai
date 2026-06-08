---
name: migration-config-skill
description: Holds canonical source and target environment parameters and verified DataStore mappings.
metadata:
  environments:
    source:
      project_number: "<SOURCE_PROJECT_NUMBER>"
      project_id: "<SOURCE_PROJECT_ID>"
      region: global
      engine_id: "<SOURCE_ENGINE_ID>"
    target:
      project_number: "<TARGET_PROJECT_NUMBER>"
      project_id: "<TARGET_PROJECT_ID>"
      region: global
      engine_id: "<TARGET_ENGINE_ID>"
  datastores_mapping:
    <id>_mcp_data: <id>_mcp_data
    <id>_google_drive: <id>_google_drive
  connectors_mapping:
    Snowflake Mcp May29: custom_mcp
    ge-drive-all: Drive
    Ge Gmail: geGmail
    googleSearch: googleSearch
    urlContext: urlContext
---

# ADK Administration Setup & Migration Instructions

This file serves as the single source of truth for cross-environment Gemini Enterprise app agent migrations. Administrators can fully configure source-to-target resource pairings by updating the YAML metadata frontmatter above.

---

## Administrative Setup Guide

### 1. Environments Configuration
Set your official canonical source and target project definitions under `environments`:
- **`project_number`**: The numeric Google Cloud Project Number (e.g., `123456789012`).
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
uv run ./migrate.py import-agent-gcs Quarterly_Business_Review_export.json --target-engine <TARGET_ENGINE_ID>
```
