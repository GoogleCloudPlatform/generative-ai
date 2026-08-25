# Curated MCP Server Catalog & Advanced Integrations

The GE Demo Generator supports Google Official MCP toolsets, Advanced Enterprise Integrations (Google Workspace OAuth Passthrough, Computer Use, Remote Slack), and Custom MCP GitHub Importers.

---

## 1. Google Built-in MCP Toolsets

| MCP Server | Transport | Tools Provided | Use Cases |
|---|---|---|---|
| **BigQuery MCP** | `StreamableHTTP` or Python Factory | `execute_sql_readonly`, `execute_sql`, `get_table_info` (the listing tools are filtered out - see `_BIGQUERY_TOOL_FILTER`) | Querying enterprise data warehouse, running analytics, anomaly detection, aggregation. |
| **Google Maps MCP** | `StreamableHTTP` or Python Factory | `search_places`, `compute_routes`, `geocode`, `reverse_geocode` | Calculating detour routes, finding nearby sites/branches, travel times. |
| **Firestore MCP** | `StreamableHTTP` or Python Factory | `get_document`, `list_documents`, `add_document`, `update_document`, `delete_document` | Managing operational records, incident states, pending tasks, ticket queues. |
| **Image Generation** | Python Custom Tool (`gemini-3.1-flash-image`) | `generate_image(prompt)` | Generating executive infographics, KPI summary charts, route maps. |

---

## 2. Google Workspace OAuth Setup & Authorization Linking

### A. Automatic Credential Discovery & Reuse
When either `enableWorkspaceAuth` or `enableWorkspaceMcp` is enabled:
1. The generator / setup script inspects Secret Manager in `$PROJECT_ID` for stored credentials:
   - `ge-demo-oauth-client-id`
   - `ge-demo-oauth-client-secret`
2. **If found**: Silently reuses them across all demos in the same Google Cloud project.

### B. Step-by-Step Interactive Guidance (When Credentials Missing)
If OAuth credentials are not found in Secret Manager, the generator / setup script presents a step-by-step setup walkthrough with exact Console deep links:

1. **Step 1: OAuth Consent Screen Setup**
   - URL: `https://console.cloud.google.com/auth/branding?project=$PROJECT_ID`
   - App Name: `Workspace MCP Servers`
   - Scopes:
     ```
     https://www.googleapis.com/auth/gmail.readonly
     https://www.googleapis.com/auth/gmail.compose
     https://www.googleapis.com/auth/gmail.modify
     https://www.googleapis.com/auth/drive.readonly
     https://www.googleapis.com/auth/drive.file
     https://www.googleapis.com/auth/calendar.calendarlist.readonly
     https://www.googleapis.com/auth/calendar.events.freebusy
     https://www.googleapis.com/auth/calendar.events.readonly
     https://www.googleapis.com/auth/calendar.events
     https://www.googleapis.com/auth/chat.spaces.readonly
     https://www.googleapis.com/auth/chat.memberships.readonly
     https://www.googleapis.com/auth/chat.messages.readonly
     https://www.googleapis.com/auth/chat.messages.create
     https://www.googleapis.com/auth/directory.readonly
     https://www.googleapis.com/auth/userinfo.profile
     https://www.googleapis.com/auth/contacts.readonly
     ```
2. **Step 2: Create OAuth 2.0 Client ID (Web Application)**
   - URL: `https://console.cloud.google.com/auth/clients/create?project=$PROJECT_ID`
   - Type: `Web application`
   - Authorized Redirect URIs:
     - `https://vertexaisearch.cloud.google.com/oauth-redirect`
     - `https://vertexaisearch.cloud.google.com/static/oauth/oauth.html`
   - User copies Client ID and Client Secret.
3. **Step 3: Configure Google Chat API (Required for Chat MCP)**
   - URL: `https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat?project=$PROJECT_ID`
   - App Name: `Chat MCP`
   - Disable interactive features; make visible to domain.
4. **Step 4: Automatic Secret Manager Storage & Authorization Creation**
   - Stores `ge-demo-oauth-client-id` and `ge-demo-oauth-client-secret` in Secret Manager for perpetual reuse.
   - Invokes Discovery Engine API to create Authorization resource:
     `POST https://discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_ID/locations/global/authorizations?authorizationId=$AUTH_ID`
   - Binds agent during publish: `agents-cli publish gemini-enterprise --authorization-id=...`

---

## 3. Advanced Integrations (Computer Use, Custom MCP, Slack)

### A. Computer Use / Browser Automation (`enableComputerUse`)
- Uses Playwright async browser runner in container.
- Tools exposed to the agent (only two - the individual click/type/scroll actions are
  driven by the Computer Use model inside the loop, not callable separately):
  - `start_browser_session()` - reserves a live-view session id and returns
    `{session_id, live_view_url}` instantly. Call it FIRST so the live-view link can be
    shown before the blocking browse begins; `live_view_url` is empty when no Data Viewer
    is deployed.
  - `computer_use_browse(goal, start_url, session_id="")` - runs the autonomous browse to
    completion and returns the result. Blocks until finished.
- The Data Viewer serves the matching `/browser-view` page; that is a Flask route, not an
  agent tool.
- **Build changes required.** Computer Use does not work on the default image. Uncomment
  the `enableComputerUse` block in `requirements.txt` (`playwright==1.55.0`,
  `google-genai>=2.7.0,<3.0.0`, `opentelemetry-exporter-gcp-logging>=1.12.0a0,<2.0.0`,
  `opentelemetry-resourcedetector-gcp>=1.12.0a0,<2.0.0`) **and** the matching
  `RUN playwright install --with-deps chromium` layer in the `Dockerfile`. All four
  requirement lines go together - the two OTel floors exist only so uv will resolve the
  pre-release Google Cloud OTel packages that `google-genai>=2.7.0` transitively needs.

### B. Custom MCP GitHub Importer (`customMcpRepos`)
- Clones target GitHub repository.
- Generates `_run.py` launcher script.
- Registers dynamic `McpToolset` in `tools.py`.

### C. Remote Managed MCP (an entry in `customMcpRepos`, not a flag)
Slack is the common case, but it is configured as a remote entry in the same import list as
the GitHub sidecars rather than through a switch of its own - there is no `enableSlackMcp`.
- Connects to the remote MCP endpoint with a Bearer token from Secret Manager.
- For Slack: posts rich BlockKit interactive cards.
