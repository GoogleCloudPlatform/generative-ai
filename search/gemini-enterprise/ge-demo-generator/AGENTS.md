# AGENTS.md — AI Agent Development Guide for GE Demo Generator

> **Purpose**: Project-specific knowledge for AI coding agents (Antigravity, Cursor, Copilot, etc.)
> and humans working on this sample.

---

## 1. Architecture

```
app/Code.gs (Apps Script backend, ~5,300 lines)
  ├─ UI server + Gemini calls (demo planning, data synthesis)
  └─ generateSetupScript(): emits a bash setup script that
       1. fetches agent_template/ from this repo at a PINNED ref
          (sparse git checkout of TEMPLATE_SUBDIR at TEMPLATE_REF)
       2. copies the static Python/JSON files into the demo project
       3. writes small per-demo config next to them:
            .env                      (scalars + feature flags)
            adk_agent/app/generated_instruction.md
            adk_agent/app/mcp_config.json
       4. builds the container and deploys to Cloud Run

agent_template/ (real, testable files — fetched at setup run time)
  ├─ adk_agent/app/agent.py            ADK agent (reads env + config files)
  ├─ adk_agent/app/tools.py            toolsets (env-gated feature blocks)
  ├─ adk_agent/app/fast_api_app.py     A2A/FastAPI runtime
  ├─ adk_agent/app/part_converters.py  A2UI part conversion
  ├─ adk_agent/app/examples/0.8/*.json A2UI few-shot examples
  ├─ managed_agent/                    Managed Agent provisioning helpers
  │                                    (create_managed_agent.py, warmup_managed_agent.py)
  ├─ demo_skills/                      Deliverable craft skills mounted into the
  │                                    Managed Agent sandbox (SKILL.md packs)
  └─ viewer_app/                       Firestore data viewer (Cloud Run Functions)
```

Per-demo variation is passed at run time, never baked into the Python:

| Mechanism | Contents |
|---|---|
| Environment variables | `DEMO_DATASET`, `FS_COLLECTION`, `REFERENCE_DATE`, `PUBLIC_DATASET_ID`, `ENABLE_WORKSPACE_MCP`, `ENABLE_COMPUTER_USE`, `ENABLE_MANAGED_AGENT`, `ENABLE_WORKSPACE_AUTH`, `MANAGED_AGENT_ID`, `MANAGED_AGENT_SKILLS_SOURCE` (plus the pre-existing `DEMO_ID`, `DATA_VIEWER_URL`, …) |
| `generated_instruction.md` | The Gemini-generated system instruction for the demo |
| `mcp_config.json` | Imported MCP servers (name, entrypoint, port, auth type) |
| Placeholders substituted by the setup script | `[CURRENCY]` in the example JSONs; `__GE_FS_COLLECTION__` / `__GE_DASH_TITLE__` / `__GE_DASH_DESC__` in `viewer_app/main.py` |

## 2. Editing rules

### 2.1 agent_template/ — plain Python and JSON

Edit directly. No escaping rules apply. Validate with:

```bash
python3 validate_examples.py   # json.loads every example + py_compile every .py
```

Feature-dependent code is gated at run time, not generation time:

```python
if os.environ.get("ENABLE_WORKSPACE_MCP") == "1":
    ...workspace toolsets...
```

Keep that pattern — do not reintroduce generation-time code selection.

### 2.2 Code.gs — remaining generated bash

`generateSetupScript` still emits bash (BigQuery/Firestore provisioning,
Dockerfile assembly, deployment). Inside those JS template literals:

- Emit a literal bash `${VAR}` as `\${VAR}`; a literal backtick as `` \` ``.
- `\` + newline inside a JS template literal is a line continuation (the
  newline disappears from the output). Use it only intentionally.
- Quoted heredocs (`cat <<'X'`) pass content through verbatim; unquoted
  heredocs (`cat <<X`) expand `$VAR` at run time.

### 2.3 ADK instruction template engine hazard (applies to agent.py)

ADK's `inject_session_state()` scans the agent `instruction` with the regex
`r'{+[^{}]*}+'` before every LLM request and raises
`KeyError: 'Context variable not found: ...'` for unknown names — crashing the
request. `{var}`, `{{var}}`, and `{{{var}}}` are all matched; double-bracing
does NOT escape.

- WRONG in instruction text: `.../collection/{document_id}`, `/form/item_{i}_name`
- RIGHT: `.../collection/<document_id>`, `/form/item_i_name` (or `[i]`)

`[BRACKET]` and `<angle_bracket>` notations are safe. This is why the
instruction pipeline uses `[PROJECT_ID]`-style tokens with `str.replace`.

## 3. Managed Autonomous Agent (`enableManagedAgent`)

Optional feature (default ON in the UI) that provisions a Pre-GA **Managed
Agents API** agent (Antigravity harness, location `global` only) the ADK agent
can delegate long-running autonomous work to over the **Interactions API**
(REST + SSE via httpx — intentionally no new pinned dependency).

- **Flag thread**: `index.html` toggle → `generateSetupScript` → PHASE A
  (right after the dashboards bucket exists: skills upload to
  `gs://<dash-bucket>/skills`, `managed_agent_instruction.txt` heredoc,
  `create_managed_agent.py start`) → `.env` + Cloud Run env
  (`ENABLE_MANAGED_AGENT`, `MANAGED_AGENT_ID`, `MANAGED_AGENT_SKILLS_SOURCE`)
  → env-gated blocks in `tools.py` / `agent.py` / `fast_api_app.py` → PHASE B
  (after Cloud Run deploy + GE registration: `create_managed_agent.py wait`
  polls readiness, `warmup_managed_agent.py` stores the environment id in
  Firestore `<demo>_managed_agent_state/current`). The A/B split hides the
  ~8-10 min agent creation behind the rest of the setup.
- **`enableWorkspaceAuth` (auth-only mode)**: sets up the GE OAuth
  authorization WITHOUT the Developer-Preview Workspace MCP servers (no
  allowlist needed). Derived gates: `workspaceAuthEnabled = enableWorkspaceMcp
  || enableWorkspaceAuth` (auth infra) and `driveHandoffEnabled =
  enableManagedAgent && workspaceAuthEnabled` (Drive save tool, gws skills,
  Workspace handoff instructions). The same derivation exists in the Python
  templates as `ENABLE_WORKSPACE_MCP`/`ENABLE_WORKSPACE_AUTH` env guards.
- **Pins**: `Api-Revision` is pinned in TWO places — `tools.py`
  (`_INTERACTIONS_API_REVISION`) and `warmup_managed_agent.py`. Update both.
  The base agent version pin lives in `create_managed_agent.py`
  (`BASE_AGENT`, env-overridable via `MA_BASE_AGENT`) and self-heals from the
  API's 400 error listing when rejected.
- **API quirks (verified live)**: the agent-create LRO never reports
  `done: true` — readiness is polled with GET on the agent itself; the
  completion SSE event carries no output text — reports are concatenated
  `step.delta` text chunks; a fresh interaction `environment` does NOT
  inherit the agent's `base_environment` — every sandbox spec must restate
  network + skills sources.
- **Skills**: deliverable craft skills are real files under
  `agent_template/demo_skills/` (professional-document,
  professional-presentation, web-report). The setup script copies them from
  the fetched template into `skills/`, uploads them to the dashboards bucket,
  and mounts them into the sandbox. The Google Chrome
  `modern-web-guidance` skill is cloned fresh from GitHub at setup time.
- **Tunables** (env): `MANAGED_AGENT_SYNC_WAIT_S` (30),
  `MANAGED_AGENT_MAX_RUNTIME_S` (1800), `MANAGED_AGENT_POLL_EXTRA_S` (3600).
- **Pre-browse (v11.22+)**: a third derived gate, `preBrowseEnabled =
  enableManagedAgent && enableComputerUse`, threads Computer-Use browser
  findings into delegations: interactive site operation always stays with the
  root agent's real browser; for composite jobs the browse runs FIRST and its
  result_summary is passed via `input_data`. In the templates this appears as
  `ENABLE_COMPUTER_USE`-guarded splice fragments inside the Managed-Agent
  blocks (`_MA_CU_BROWSER_EXCLUSION`, `_MA_PREBROWSE_EXCEPTION` in
  fast_api_app.py and the CU-conditional fragments in agent.py).
- **Workspace token freshness (v11.6+)**: `session.state` only ever holds the
  CREATE-time OAuth token (ADK's InMemorySessionService returns copies), so
  the runtime keeps two always-fresh sources — the process-global
  `builtins._workspace_oauth_token` and the per-session
  `builtins._ws_session_tokens` registry — and `_workspace_header_provider`
  tries them freshest-first. Do not "simplify" back to state-based lookup.

## 4. Template fetch pinning (TEMPLATE_REF)

The generated setup script fetches `agent_template/` at a commit SHA that is
resolved at script-GENERATION time. `CONFIG.TEMPLATE_REF` (Script-Properties
overridable, together with `TEMPLATE_REPO` and `TEMPLATE_SUBDIR`) defaults to
the branch name `main`: `generateSetupScript` resolves it to a concrete
commit SHA via the GitHub commits API and bakes THAT SHA into the script, so
every generated script is reproducible while this repository never has to
commit its own merge SHA (no re-pin PRs). Setting the `TEMPLATE_REF` Script
Property to a 40-hex SHA hard-pins and skips resolution.

Safety nets — keep all three working:

- Generation time, resolvable branch: the ref is replaced by its commit SHA.
- Generation time, API unreachable: the script falls back to fetching the
  ref as written (branch tip) and a NOTE banner in the preview explains the
  reproducibility caveat; a dead hard-pinned SHA gets a WARNING banner.
- Run time: the fetch step exits with a clear message if the ref cannot be
  fetched.

Pre-merge testing: point the `TEMPLATE_REPO` / `TEMPLATE_REF` Script
Properties at the fork/branch under review (resolution then pins the fork
branch tip). Delete both properties after the upstream merge.

## 5. Release checklist

1. Edit `agent_template/` and/or `app/` files; run `python3 validate_examples.py`.
2. Bump `APP_VERSION` in `app/Code.gs`.
3. Commit, push, and merge — no TEMPLATE_REF update is needed (generated
   scripts self-pin to the merge commit at generation time).
4. `clasp push` the `app/` files AFTER the upstream merge (or before it with
   the `TEMPLATE_REPO`/`TEMPLATE_REF` Script Properties pointed at the review
   fork/branch); deploy a test demo end to end.

## 6. Deployment anti-patterns (learned the hard way)

- **No background processes for sequential dependencies** in the setup script:
  `docker build &` followed by a dependent step races; keep dependent steps
  sequential (background only truly independent work, then `wait`).
- **`--ingress internal` does not block Google-internal callers** — Gemini
  Enterprise reaches the service through Google's network; do not rely on
  ingress alone for auth decisions.
- **No iterative blind fixes**: when a deploy fails, read the Cloud Run
  startup logs (`SyntaxError`, MCP sidecar readiness, `/.well-known/agent.json`)
  before changing code.
- **Modify files with byte-exact tools**: when scripting edits to Code.gs or
  the templates, operate on raw bytes/strings, not on regex replacements with
  `\n` in the replacement text (Python `re` interprets them).

## 7. Verification

- `python3 validate_examples.py` — template JSON + Python compile checks.
- `bash -n` any generated setup script before running it.
- After deploy: Cloud Run startup logs, `✅ N/N MCP sidecars ready`,
  `/.well-known/agent.json` responds, model name shows in the thinking
  accordion.
