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
  └─ viewer_app/                       Firestore data viewer (Cloud Run Functions)
```

Per-demo variation is passed at run time, never baked into the Python:

| Mechanism | Contents |
|---|---|
| Environment variables | `DEMO_DATASET`, `FS_COLLECTION`, `REFERENCE_DATE`, `PUBLIC_DATASET_ID`, `ENABLE_WORKSPACE_MCP`, `ENABLE_COMPUTER_USE` (plus the pre-existing `DEMO_ID`, `DATA_VIEWER_URL`, …) |
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

## 3. Template fetch pinning (TEMPLATE_REF)

The generated setup script fetches `agent_template/` at the commit pinned in
`CONFIG.TEMPLATE_REF` (Script-Properties overridable, together with
`TEMPLATE_REPO` and `TEMPLATE_SUBDIR`). Pinning to a commit SHA keeps every
generated script reproducible; never point it at a moving branch.

Two safety nets exist — keep both working:

- Generation time: Code.gs checks the ref via the GitHub API and prepends a
  warning banner to the script preview if it is unreachable.
- Run time: the fetch step exits with a clear message if the ref cannot be
  fetched.

## 4. Release checklist

1. Edit `agent_template/` and/or `app/` files; run `python3 validate_examples.py`.
2. Bump `APP_VERSION` in `app/Code.gs`.
3. Commit and push; note the commit SHA that contains the final
   `agent_template/`.
4. Update `TEMPLATE_REF` in `app/Code.gs` (or the Script Property) to that SHA
   and push that change too.
5. `clasp push` the `app/` files; deploy a test demo end to end.

## 5. Deployment anti-patterns (learned the hard way)

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

## 6. Verification

- `python3 validate_examples.py` — template JSON + Python compile checks.
- `bash -n` any generated setup script before running it.
- After deploy: Cloud Run startup logs, `✅ N/N MCP sidecars ready`,
  `/.well-known/agent.json` responds, model name shows in the thinking
  accordion.
