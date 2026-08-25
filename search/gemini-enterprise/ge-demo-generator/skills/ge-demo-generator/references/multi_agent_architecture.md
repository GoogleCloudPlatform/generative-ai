# Multi-Agent Architecture & Routing Reference

The synthesized demo agent employs a **Triple-Agent Architecture** built on the Google Agent Development Kit (ADK) and **Gemini 3.7 Flash**:

```
┌──────────────────────────────────────────────────────────────┐
│  root_agent (Coordinator + A2UI Builder)                     │
│  Model: gemini-3.7-flash (AGENT_MODEL_LITE)                  │
│  Role: Main conversation, greetings, simple queries,         │
│        building A2UI cards, routing to sub-agents.           │
│                                                              │
│  Sub-Agents:                                                 │
│  ├── deep_analysis_agent (Inline Analytical Sub-Agent)       │
│  │   Model: gemini-3.7-flash (AGENT_MODEL)                   │
│  │   Role: Complex inline multi-step analytical reasoning.   │
│  │   Transfer: Returns control to root_agent on completion.  │
│  │                                                           │
│  └── background_agent (Standalone Async Worker)              │
│      Model: gemini-3.7-flash (AGENT_MODEL)                   │
│      Role: Deep batch operations & long-running pipelines.   │
│      Trigger: Invoked via /execute_task endpoint.            │
└──────────────────────────────────────────────────────────────┘
```

---

## 1. Routing Logic & Guidelines

1. **Simple Conversation / Greetings**:
   - Handled directly by `root_agent`.
   - Renders Welcome Onboarding Card on first turn.

2. **Background-First Routing Policy (Analytical / Multi-Step Queries)**:
   - For complex analytical tasks (cross-table correlations, predictive reviews):
     - The `root_agent` MUST propose running it as a background task **first** via A2UI suggestion chips (`[Run deep analysis in the background]` vs `[Analyze inline now]`; render the labels in the conversation language).
     - **If Background**: Calls `register_background_task`, which posts to `/execute_task` or Cloud Tasks.
     - **If Inline**: Transfers control to `deep_analysis_agent`.

3. **Workflow Execution Routing**:
   - When the user triggers an operational workflow (e.g. from a Workflow Execution Plan card), bypass inline transfer and register the background task directly.

---

## 2. Background Worker Pipelines & Anti-Shallow Guard

The `background_agent` executes in one of two structured operational pipelines:

### Pipeline 1: Operational Workflow (`SCAN -> ANALYZE -> PLAN -> EXECUTE -> VERIFY -> REPORT`)
- **Scan**: Queries BigQuery/Firestore for pending operational events or anomalies.
- **Analyze**: Calculates impact, costs, or delays.
- **Plan**: Formulates concrete mitigation steps (e.g. route changes, inventory reallocations).
- **Execute**: Applies updates via Firestore/BigQuery MCP tools. High-risk operations require human confirmation.
- **Verify**: Re-queries systems to confirm state resolution.
- **Report**: Generates structured executive markdown report.

### Pipeline 2: Deep Statistical Review (`COLLECTION -> EXPLORATORY -> STATISTICAL -> SYNTHESIS -> REPORT`)
- Queries multiple tables.
- Computes aggregates, percentiles, correlation metrics.
- Summarizes findings with 3+ actionable business recommendations.

### Anti-Shallow Guard Checklist
The worker is prohibited from shallow hand-waving. It MUST:
1. Query at least 2 distinct data sources or tables.
2. Cite exact numerical metrics and IDs from queries.
3. Provide at least 3 concrete, high-impact business recommendations.

---

## 3. ADK Configuration Best Practices

1. **Model Selection**:
   - Standard: `gemini-3.7-flash` (Highest quality, native reasoning, sub-second latency across all agent tiers).

2. **Placeholder Escaping Rule**:
   - In agent instructions (`base_instruction`), NEVER use `{variable_name}` or `{{variable_name}}`. ADK's `inject_session_state` regex matches all `{...}` and will crash with `KeyError`.
   - **Always use `<variable_name>` or `[VARIABLE_NAME]`.**

3. **Context Caching**:
   - Configure `ContextCacheConfig(min_tokens=2048, ttl=3600)` on the ADK `App` to keep large system instructions and tool definitions cached in the Vertex AI Agent Platform.

4. **Plugins & Callbacks**:
   - `ReflectAndRetryToolPlugin`: Automatically catches tool execution errors (e.g. SQL syntax errors) and feeds them back to Gemini for self-correction.
   - `inject_image_callback`: Automatically extracts generated image artifacts from session state and embeds them in the response.
   - `LoggingPlugin`: Logs token usage, tool calls, and model latency to Cloud Logging.

---

## 4. The Autonomous Sandbox Agent's System Instruction

`enableManagedAgent` is the one default-ON capability, and it is switched on by a
file, not by the flag alone: `setup_and_deploy.sh` skips the whole autonomous
agent when `scripts/managed_agent_instruction.txt` is missing, and the deploy
succeeds anyway - with `delegate_autonomous_task` answering `unavailable` and
demo prompts 5 and 7 unable to run. Copy the template from
`templates/scripts/managed_agent_instruction.txt` like every other scaffolded
file and edit it; do not write one from scratch.

**What to substitute**

| Placeholder | Replace with | Who does it |
|---|---|---|
| `[BUSINESS_CONTEXT]` | The same domain knowledge you wrote into `agent.py`'s `gen_instruction`: company profile, table and column semantics, the Firestore task shape, the staged Drive files. Written in the demo's own language. | You, during Phase 4 |
| `[DATASET_ID]`, `[COLLECTION_ID]` | The dataset and collection names. | `setup_and_deploy.sh`, at deploy time |

The sandbox agent has **no** database tools - the instruction names the dataset
and the collection only to tell it what it must not try to reach. That is why
the two names have to resolve: left as literals, the guardrail stops matching
what the delegating assistant actually says.

**Blocks to add when a flag is on.** The template ships the default
configuration (Workspace off, computer use off, skill packs mounted). Turn one
of those on and the matching block below has to be inserted, or the sandbox
agent will not know it has the capability.

`enableWorkspaceAuth` or `enableWorkspaceMcp` - REPLACE the `WORKSPACE LIMITS`
block with:

```text
WORKSPACE ACTIONS
- When the task message contains a WORKSPACE ACCESS section, you can act on the requesting user's Google Workspace via the gws CLI (Gmail drafts, Chat messages, Calendar events, Drive). Export the provided token as instructed, and consult the gws-* skills under /workspace/.agent/skills first.
- INSTALLING gws: the warm-up usually pre-installs it at $HOME/bin/gws (invoke it by that absolute path - PATH exports do not persist between commands). If it is missing, install the static musl binary: mkdir -p $HOME/bin && curl -sL https://github.com/googleworkspace/cli/releases/latest/download/google-workspace-cli-x86_64-unknown-linux-musl.tar.gz | tar xz -C $HOME/bin ./gws && chmod +x $HOME/bin/gws. Do NOT install via npm: the npm-delivered Linux binary requires GLIBC 2.39, which this sandbox does not have, and plain npm -g also fails with EACCES (no root).
- CHAT POSTING FAILURES: if a Chat post fails with a 403 / PERMISSION_DENIED / configuration error, the cause is almost always that the demo project has not completed the ONE-TIME Google Chat API app configuration (a console step in the setup tutorial). State EXACTLY that in your report, include this link for the admin: https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat - and include the full message text you intended to post so the assistant can relay it. NEVER invent explanations like security restrictions or tenant policy.
- DRIVE SAVES: when the task asks for a file saved to the user's Google Drive as Google Slides / Docs / Sheets, upload it with the gws CLI using Drive import-conversion (office file uploaded with the target Google mime type). Do it as soon as the file is ready, verify by reading the file metadata back, and put the returned webViewLink in your report. If the Drive upload fails, still deliver the file through the upload URLs and say the Drive save failed so the assistant can retry it.
- DRIVE SAVES: when the task asks for a file in the user's Google Drive (or as Google Slides / Docs / Sheets), upload it yourself with the gws CLI using an import-conversion to the native Google format (pptx to Google Slides, docx to Google Docs, xlsx to Google Sheets), then include the returned Drive webViewLink in your report. ALSO upload the original office file to the matching deliverable upload URL as a backup.
- Do Workspace operations EARLY in the task: the token expires after about an hour.
- HARD GUARDRAILS: never SEND email (drafts only, unless the task explicitly says to send); never delete anything in Workspace; post Chat messages only to spaces the task explicitly names; never write the token into your report, logs, code, or files.
- ADMIN LIMITS: the provided token always carries USER-level scopes only - Admin SDK APIs (Directory, Reports / audit logs, license management) and org-wide admin operations fail with 401/403 by design, and no admin credentials will ever be provided. Never retry or loop on these calls: report the limitation clearly and complete the task from data the user-level APIs can see (for example the user's own Drive file metadata and sharing settings).
- CHAT SPACES: when the task names a Chat space, search for it first; if no space with that name exists, CREATE the space with that exact name via the gws CLI and then post there (demo environments often lack the space - creating it is expected, not an error). State in your report that you created it. If creation fails (e.g. missing permission), report the failure instead of posting elsewhere.
- EMAIL ENCODING: non-ASCII email headers (Subject, display names) MUST be RFC 2047 MIME-encoded (for example =?UTF-8?B?...?=). After creating a draft, read it back and verify the subject decodes correctly; delete and recreate it if it is garbled.
- REPORTING DRAFTS: when you create a Gmail draft, your report must state it ALREADY EXISTS in the user Gmail Drafts folder, with the draft subject and this link: https://mail.google.com/mail/u/0/#drafts - never paste the full email body into the report for manual copying.
- If no WORKSPACE ACCESS section is present, you have no Workspace access for this task - say so in the report instead of guessing.
```

`enableComputerUse` - INSERT after the `DATA ACCESS` block:

```text
BROWSER FINDINGS
- When the task message contains a "BROWSER FINDINGS" block inside INPUT DATA, it is live web data gathered moments before delegation by the requesting assistant using its real interactive browser. Treat it as fresh and authoritative: build on it, cite its source URLs in your deliverables, and do NOT spend steps re-fetching the same pages.
- You have NO interactive browser yourself. If additional web information is needed beyond the findings, use your read-only tools (Google Search, web page reading). If a page truly requires interaction (login, form entry, clicking through an app), state that limitation in your report instead of attempting it, and never claim you operated a browser.
```

An operating-model description agreed in Phase 2 - INSERT after
`--- END BUSINESS CONTEXT ---`:

```text
--- OPERATING MODEL (organizational context) ---
[OPERATING_MODEL]
Frame your deliverables within this operating model: attribute findings to the departments that own the data, address recommendations to the department that owns the decision, and describe hand-offs between departments explicitly.
--- END OPERATING MODEL ---
```
