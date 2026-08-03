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
  This applies to *prose* inside an emitted Python heredoc too — a comment
  written in Markdown style ends the enclosing template literal, and the
  resulting `SyntaxError` points at whatever token follows, never at the
  backtick. Reword rather than escape.
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

### 2.4 Do not ask a model to detect a language the UI already knows

Prompts here stay language-agnostic — no hardcoded Japanese or English
examples, so the model answers in the user's language. That is about not
*biasing* the choice; it is not a licence to make the model *guess* it.

`optimizeGoalWithMagicWand` used to open with a four-clause "CRITICAL
MULTILINGUAL RULE" that enumerated candidate languages ("English, Japanese,
German, French, Spanish, Chinese, Korean, etc.") and leaned on negations ("you
MUST NOT output in that associated language unless..."). Measured against
`gemini-3.5-flash-lite`, an **English** Manhattan retail scenario came back
**fully German in 2 of 5 runs**, with a third mixed. Handed a menu of
languages, the model sometimes picks one off it.

The frontend already knows the intended language — the Template Hub selector,
or the research language while research is in play — so `getOptimizeLanguage()`
passes it in `capabilityOpts.language` and the prompt states it once,
positively: `**OUTPUT LANGUAGE (MANDATORY)**: Write the entire output in
<Language>.` English then held in 8 of 8 runs.
`resolveOutputLanguage_()` accepts both vocabularies the UI has to hand
(Template Hub codes like `en`, research names like `Deutsch`) and returns `''`
for anything else, which leaves the caller on a detection-only fallback.

Two things worth keeping in mind if you touch this:

- **The stated language wins outright.** A draft added "unless the input is
  written in another language, then use that instead" as a safety net. It was
  measured: the model ignored it in 6 of 6 runs, so it was removed rather than
  kept as a clause that reads like coverage and provides none. The consequence
  is real — a scenario typed in Japanese with the selector on English comes
  back in English. The selector is the control for that.
- **Test language behaviour by sampling, not once.** The original bug
  reproduced in 2 of 5 runs; a single green run would have "confirmed" a prompt
  that was broken 40% of the time.

### 2.5 A2UI card delivery and press context

Two failure modes found together on one live turn (a scanned-fax-to-quote
workflow): the card the model tried to draw never appeared, and the answers the
user picked on the card that did appear never reached the agent.

**A `beginRendering` without a `surfaceUpdate` renders nothing.**
`beginRendering` only OPENS a surface; the component tree arrives in
`surfaceUpdate`. The model emitted `[beginRendering, dataModelUpdate]` and moved
straight on to the suggestions block, so the client opened an empty surface and
the user saw prose plus chips and no card. Nothing was dropped server-side. The
"emit begin AND update in the SAME block" rule existed, but only inside the
SUGGESTION CHIPS bullet, so it read as a chips rule; it is now stated as a
general A2UI rule at both prompt sites and in the Pattern (J) batch-editor
template, with `dataModelUpdate` called out explicitly as *not* a substitute.
The server-side guard was suggestions-only in the same way
(`_chips_ok` → `[chip_reprompt]`). `_orphan_card_surface_ids()` now reports any
non-suggestions surface that was opened but never populated; the executor drops
those parts (an unpopulated surface can only render blank, and it would also pin
that surfaceId for later turns) and runs ONE card-only re-prompt, keeping the
result only if it is populated and orphan-free. Logged as `[card_reprompt]`, and
it runs BEFORE the chip recovery so a recovered card with its own buttons
suppresses the chip re-prompt, and before the idempotency/artifact caches so
replays serve the complete version.

**An action context key must never equal a component id.** A Start press on the
autonomous briefing card arrived with every question collapsed into a single
literal key:

```json
"context": {"[object Object]": "What is the preferred time range...?",
            "a0": ["Store Management Group"], "a1": ["Last 90 days"],
            "ra": "1", "s0": "..."}
```

`a<i>`, `s<i>`, `ra` and `text` all survived, and multi-key contexts work
elsewhere (a batch-editor Submit delivers `item_0_qty`,
`item_0_selected_sku`, … intact), so neither the message-prep chain nor the
array-of-`{key, value}` shape is at fault — that shape matches the A2UI 0.8
catalog. The one thing that distinguished `q<i>`: it was ALSO the component id
of the question `Text`. A context key that collides with a component id is
resolved against the client's component registry and stringified into the key,
losing the value. Fix: the question `Text` keeps id `qt<i>` while the label
travels as `bq<i>` — no key/id pair may ever be equal. The shipped few-shots
were already safe by accident (`fTitle` vs key `title`); a prompt rule now makes
that explicit so model-authored cards cannot reintroduce it.

Independently, `_extract_briefing_answers` gated its per-question loop on
`q<i>` being present, so a mangled label discarded answers that had arrived
perfectly. Harvesting is now driven by the ANSWER (`a<i>`, falling back to
`s<i>`); the label is optional and only affects the wording of the recap line.
**Never gate a press handler on a decorative context key.**

**The recovery harvest must not swallow parse errors.** On a later turn of the
same workflow the `[card_reprompt]` above fired correctly and the re-prompt came
back with a complete tagged card, yet the turn still ended `re-prompt yielded no
usable card`. The harvest runs through `_extract_report_parts`, which had
`except Exception: _rps = []` around `process_chunk` — no log, no fallback. The
parser raised the same recurring schema `ValueError` (`'alignment',
'distribution' were unexpected`) that the main loop heals through its CRITICAL
FALLBACK, but here the exception was eaten silently, and the untagged safety net
below it is explicitly gated on `'<a2ui-json>' not in _text`, so a *tagged*
block was unreachable by any recovery path at all. `_extract_report_parts` now
mirrors the main loop on parse failure: log `[report_extract] A2UI stream parse
error`, regex-extract the tagged blocks, `_parse_loose_json` +
`_heal_a2ui_message_list` + `create_a2ui_parts`, and keep the plain-text
remainder (dict-repr guard still applied). That one function serves the synth
retry, the card re-prompt AND the chip re-prompt — a silent `except` there turns
every recovery path into a no-op precisely on the turns that need recovery most.

**The healer must prune model-invented component properties, or the schema gate
re-drops every re-prompt.** Next attempt on the same card: the fallback above
fired and healing ran, but the card was *genuinely* schema invalid —
`MultipleChoice` carrying a top-level `label` (`'label' was unexpected`).
`label` is legal on `TextField` / `CheckBox` / `Slider` in the 0.8 catalog but
NOT on `MultipleChoice`, which only has per-option labels; that asymmetry is one
models trip on constantly. `_normalize_a2ui_shapes` could not repair it, so
`_a2ui_msg_schema_ok` dropped the `surfaceUpdate` on the original turn AND on
the re-prompt (the model repeats its own mistake), leaving a `beginRendering` +
`dataModelUpdate` orphan pair each time. Repair (d) in `_normalize_a2ui_shapes`
now prunes unknown top-level component properties, driven by the selected
catalog's own schema (`a2ui_selected_catalog.catalog_schema['components']`, and
only for components that declare `additionalProperties: false`) — so a legal
property can never be stripped, and no hand-maintained component allowlist is
needed. Log marker: `[a2ui_heal] pruned unknown prop(s) ... from <Component>`.
Verified both directions: the live failing card validates after pruning, and the
canonical `interactive_form.json` example passes through byte-identical.

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
- **The pre-flight gate is text-only — attachments bypass it**: the classifier
  reads text parts only, so "read this fax and prepare the quote" was judged on
  its words alone, returned AUTONOMOUS, and short-circuited into the briefing
  card before the agent ran. The "IMAGE/VISION WORK IS YOURS ALONE" rule lives
  in `agent.py`, which never executed. Two changes: a READING AN ATTACHED IMAGE
  OR DOCUMENT exclusion in `PREFLIGHT_CLASSIFIER_PROMPT`, and — because a
  text-only classifier cannot be trusted with a question about a non-text part —
  a structural `_message_has_attachment()` check that sets `_gate_skip` for ANY
  turn carrying an `inline_data`/`file_data` part. No gate card is right there:
  the sandbox cannot see the attachment at all, and an inline plan card only
  adds a click to work the agent was already going to do inline. Note also that
  the confirmed-press SYSTEM NOTE pinning `delegate_autonomous_task` as the
  first action is not reliable — on that turn ADK sticky-routed into
  `deep_analysis_agent` and ran the work inline anyway. Keep gates structural,
  not advisory.
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
branch tip). `TEMPLATE_REPO` is the clone URL of the fork
(`https://github.com/OWNER/generative-ai.git`), never the browse URL of the
template directory — the latter is a web page and every script generated while
it is set dies at the template fetch. Delete both properties after the upstream
merge; a stale `TEMPLATE_REPO` keeps every generated script pointed at the fork.

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
- **`authorizations.patch` silently no-ops without `updateMask`**: a full-body
  PATCH to the Discovery Engine authorization endpoint returns **HTTP 200 and
  changes nothing**. Pass `?updateMask=serverSideOauth2`, and never treat the
  200 as proof — read the resource back and check it actually changed.
- **Authorization resources always live in `global`**: they are created at
  `projects/<id>/locations/global/authorizations/<id>` regardless of where the
  Gemini Enterprise app itself lives. Binding an agent to
  `locations/<app-location>/...` points a `us`/`eu` app at a resource that does
  not exist, which reproduces the endless re-authorization prompt.
- **A failed OAuth token exchange is invisible**: Gemini Enterprise performs
  the code-to-token exchange server-side after consent and surfaces nothing
  when it fails — no UI error, no Cloud Run log, no agent-side signal. Probe
  `https://oauth2.googleapis.com/token` with a throwaway code to tell the
  cases apart: `invalid_grant` means the credentials are fine, `invalid_client`
  means the stored secret is stale.

## 7. Verification

- `python3 validate_examples.py` — template JSON + Python compile checks.
- `python3 check_deps.py` — dependency cap audit (see section 8).
- `python3 canary.py --out /tmp/canary --run-venv` — resolve today's
  requirements and actually run the imports (see section 8.4);
  `docker build /tmp/canary` for the full image.
- `bash -n` any generated setup script before running it.
- After deploy: Cloud Run startup logs, `✅ N/N MCP sidecars ready`,
  `/.well-known/agent.json` responds, model name shows in the thinking
  accordion.

## 8. Dependency policy

These demos are built live, often minutes before a customer meeting, from
whatever the resolver picks that day. Two rules keep an upstream release from
turning that into a failed demo.

### 8.1 Every pip requirement carries a major cap

`PINNED_DEPS` in `app/Code.gs` is the single source of every pip requirement
the generated script emits. Each entry has an upper bound at the next major.

The floor-only policy this replaced is what let `mcp` 2.0.0 into builds on the
day it shipped: 2.0.0 removed `mcp.shared.session`, which `google-adk` still
imports, so every generated container died at import. `google-adk` does declare
`mcp<2,>=1.24` — but only under its `mcp`/`all`/`test` extras, and we install
`google-adk[a2a]`, so that cap never applied.

Two things to know before editing a requirement:

- **Cap at the next major above the currently RESOLVED version, not above the
  floor** — unless the resolved version is known not to work. Several bands
  deliberately span two majors (`google-adk` 1→2, `google-genai` 1→2,
  `google-cloud-storage` 2→3) because the resolver needs that room to
  backtrack.
- **What the resolver picks is not evidence that it works.** `a2a-sdk` is
  capped at `<0.4.0`, below what resolves. `google-adk` 2.5.0 widened its own
  bound from `a2a-sdk<0.4` to `a2a-sdk<2`, which let 1.x in for the first time;
  1.x removed `a2a.types.DataPart`, `a2a.server.apps` and
  `a2a.utils.constants.EXTENDED_AGENT_CARD_PATH`, breaking the a2ui interface
  check and `fast_api_app.py` at once. ADK 2.5.0 runs fine on 0.3.26, so the
  cap contains `a2a-sdk` without holding ADK back. Only a build that passes
  justifies a bound.

`agent_template/pyproject.toml` repeats four of these requirements verbatim and
is copied into the build context, so it must carry the same caps.
`check_deps.py` fails if it drifts.

A cap in `requirements.txt` only binds the install *we* issue. When a demo
imports a custom MCP server, the Dockerfile clones that repo and runs its own
`uv pip install` into the same site-packages — with bounds we did not write. So
the script also emits a `constraints.txt` (upper bounds only, derived from the
same `PINNED_DEPS`) and passes `-c /app/constraints.txt` to both branches of
that install. Upper bounds only is deliberate: a floor in a constraints file
can force an *upgrade* inside a resolution we are not steering, including into
a pre-release; a cap can only ever prevent one. Constraint files may not carry
extras or direct references, so `[a2a]` / `[agent_engines]` are stripped and
the a2ui git pin is excluded. Duplicate names are a hard error for pip, which
is why dropping the floors usefully collapses the two `google-genai` entries
into one line.

### 8.2 The build fails on a broken import, not the container

The generated `dep_smoke_test.py` runs as a Docker build step. It walks the
generated `adk_agent/` package with `ast`, collects every third-party module
and symbol the code imports, and resolves each one; imports inside `try/except`
are treated as optional and skipped. Because it derives its targets from the
generated sources, it needs no maintenance as feature flags change.

This exists because the failure mode it catches is nearly impossible to
diagnose at run time: a `ModuleNotFoundError` at import surfaces only as a Cloud Run
startup probe retrying forever, and the setup script appears to hang at
"Deploying Main Agent to Cloud Run via Source". Replayed against the `mcp`
2.0.0 incident, the smoke test names two breaks — the runtime traceback only
ever reached the first. `uv pip freeze` runs immediately before it so the
installed versions are in the build log when it fails.

**This test must never be the reason a build fails.** It has failed builds on
its own bugs twice, and both presented as the same endless "Deploying…" as a
real dependency break — strictly worse than not having the test. A file it
cannot parse is warned about and skipped, not raised. Its import pairs are
sorted with `key=lambda pair: (pair[0], pair[1] or "")`, because a plain import
yields `None` for the symbol and a from-import yields a string; the default
tuple ordering compares those two against each other the moment both forms
exist for one module, which is every real agent.

### 8.3 Auditing

`python3 check_deps.py` resolves all three requirement variants (agent,
agent + computer use, viewer) with the pinned `uv` and reports floor / cap /
resolved / latest per requirement:

- **MISSING CAP** — a requirement has no upper bound. Policy violation, exit 1.
- **PYPROJECT** — `agent_template/pyproject.toml` disagrees. Exit 1.
- **STALE CAP** — a newer major shipped above the cap. Not an error; evaluate
  it, smoke-deploy, then either raise the cap or record why it stays.
- **FLOOR DRIFT** — informational, the band spans two majors on purpose.

Add `--offline` to skip the PyPI latest-version lookups.

### 8.4 Proving today's resolution builds — `canary.py`

`check_deps.py` audits the bounds. It cannot answer the question the bounds
do not settle: *does today's resolution actually build and import?* Both real
outages — `mcp` 2.0.0 and `a2a-sdk` 1.x — passed the caps and were caught only
by running the imports. Until this script existed, the first execution of any
new resolution was a customer-facing demo build.

`canary.py` reconstructs the build context out of the repo — the requirements
for a variant, `constraints.txt`, the `__DEP_SMOKE_EOF__` heredoc verbatim, and
a module holding every import statement in `agent_template/adk_agent/` — into a
directory that can be run in a venv or built with Docker:

```bash
python3 canary.py --out /tmp/canary --run-venv     # fast path, no Docker
python3 canary.py --out /tmp/canary --variant computer-use
docker build -t ge-canary /tmp/canary              # the real image
```

Because the import surface is read out of the template with `ast`, it needs no
maintenance when the agent changes, and it is a *superset across feature
flags*: the template branches on environment variables at run time, so one run
covers configurations no single demo produces.

Two properties worth preserving if you edit it:

- Imports inside `try/except` are excluded, matching `dep_smoke_test.py`'s own
  semantics — that is also what keeps the superset installable, since Computer
  Use, the viewer and the OpenTelemetry exporters are all optional at import.
- Verify a change to it against a *known-bad* resolution, not just a green one.
  Setting the `a2a` cap back to `<2.0.0` must reproduce all three 1.x breaks.
  A canary that cannot go red is worse than no canary, because it reads as
  coverage.

**Not fixed by any of this:** there is still no lockfile. `requirements.txt` is
regenerated and re-resolved on every deploy, so the same setup script run on
two different days can produce different transitive sets within the capped
bands. Caps bound that drift; the canary tells you when the drift breaks
something; neither makes two runs reproducible.

### 8.5 Cloned MCP installs must fail the build

For every non-remote entry in the imported MCP list, the generated Dockerfile
clones the repo and installs it. Each branch of that install used to end in
`2>/dev/null || true`. Three defects, in ascending order of nastiness:

1. `2>/dev/null` discarded the stderr that names the cause.
2. A failed install produced a **green image**. Nothing else in the build
   imports the cloned server, so the failure resurfaced as a sidecar that came
   up and could not serve a tool call — at demo time, with no build log left.
3. `( … || true )` always exits 0, so **`|| npm` was unreachable code**. The
   documented Python→Node fallback had never once run for a repo carrying
   `pyproject.toml` or `setup.py`.

Adding `-c /app/constraints.txt` (section 8.1) made (2) *more* likely, not
less: a cloned server demanding `mcp>=2` now fails resolution, and that
failure — the one the constraints file exists to produce — was the one being
swallowed. A guard whose alarm is wired to `/dev/null` is worse than no guard.

The install is now built from three pieces, chosen by position:

| Piece | Where | On failure |
|-------|-------|------------|
| `pipStrict` | primary, Python repos | fails → hands over to the Node fallback; no Python manifest at all also counts as failure, so the fallback is reachable |
| `npmCmd` | primary on Node repos, last resort on Python repos | fails → fails the build |
| `pipBonus` | trailing extra on Node repos, for hybrid servers | prints `WARNING:`, build continues |

`npm run build` is skipped when `npm pkg get scripts.build` returns `{}`, and
fatal when the repo declares one and it fails — a half-built TypeScript server
is precisely the image that starts and then cannot answer a tool call.

This is deliberately breaking: builds that used to go green now stop. Every one
of them was producing an image with its MCP dependencies missing. If you touch
this block, re-check the shell cases against stubbed `uv`/`npm` — the failure
mode it guards against is invisible in a passing build by construction.

## 9. Managed remote MCP servers

Before this feature landed, "remote MCP" meant Slack and only Slack. The generic
rail existed on paper — `mcp.type === 'remote'` had an `else` branch in the
setup script — but it was dead code: `tools.py` filtered every remote entry out
of the toolset list, the system instruction described any remote server as
Slack, the catalog's `addCatalogServer()` stamped
`SLACK_CLIENT_ID` / `SLACK_CLIENT_SECRET` onto every remote entry, and secret
binding fell through to the sidecar path, which derives secret names from
`github_url` — a docs link for a managed server. The rail is now real, with
Notion in the catalog as its first user.

### 9.1 Auth modes are discovered, not hardcoded

`probeRemoteMcpServer(url)` (Code.gs) classifies an endpoint by protocol
discovery alone. It POSTs an unauthenticated `initialize`; a `2xx` means
`auth_type: 'none'`. A `401` sends it through RFC 9728 (`WWW-Authenticate:
resource_metadata=`, then `/.well-known/oauth-protected-resource{path}`, then
the bare path) to find the authorization server, and RFC 8414
(`/.well-known/oauth-authorization-server{path}`, bare, then
`/.well-known/openid-configuration`) to find its endpoints.

| `auth_type` | Trigger | What setup does |
|---|---|---|
| `none` | unauthenticated `initialize` succeeds | nothing |
| `oauth2_dcr` | AS metadata has `registration_endpoint` | RFC 7591 registration + PKCE authorization |
| `oauth2_manual` | AS metadata, no `registration_endpoint` | prompts for a client ID/secret, then PKCE |
| `bearer_token` | credential required, no OAuth metadata | prompts for a long-lived token |
| `oauth2_slack` | catalog entry only, never probed | the pre-existing Slack flow |

**Do not try to fold Slack into the generic path.** Slack publishes no
`registration_endpoint` and requires `client_secret_post`, so it needs a
hand-created app either way. `oauth2_slack` is a legacy branch left deliberately
untouched; changing it risks a working flow for no gain.

### 9.2 One JSON blob per server, one env var, one secret

Each generic remote server gets exactly one secret, `<dirName>-rmcp-<slug>`,
bound to one env var, `RMCP_<SLUG_UPPER>_AUTH` (see `remoteMcpSlug_`,
`remoteMcpEnvKey_`, `remoteMcpSecretName_` in Code.gs). The blob is
`{access_token, refresh_token, client_id, client_secret, token_endpoint,
resource, expires_in, issued_at}`. It is pushed through `optionalSecrets` so a
skipped or failed authorization still deploys — the agent logs the missing
server and starts without it, rather than failing the whole deploy.

At run time `get_remote_mcp_toolsets()` builds one `McpToolset` per server with
`tool_name_prefix=<slug>` (so several remote servers cannot collide) and a
`header_provider` that refreshes 120 s before expiry. Rotated refresh tokens are
written back with the Secret Manager REST `:addVersion` endpoint using
`google.auth` + `httpx` — both already imported in `tools.py`. **Do not add
`google-cloud-secret-manager` for this**; a new pip dependency in the agent
image is a much bigger cost than a 15-line REST call, and section 8 explains why
every added dependency is a build-break risk.

Servers with no `expires_in` but a refresh token get `_RMCP_DEFAULT_TTL = 2700`,
so a provider's silence does not turn into a token that is never refreshed.

### 9.3 Per-demo variation stays in `mcp_config.json`

`agent_template/` is static (section 2.1), so nothing about a specific server may
be generated into `tools.py`. Code.gs precomputes everything the template needs
into the `mcp_config.json` entry — `generic`, `prefix`, `env_key`, `secret`,
`endpoint_url`, `auth_type`, `description`, `capabilities` — exactly the same
contract the local (sidecar) entries already use for `safe_name` / `port` /
`local_idx`. `get_remote_mcp_configs()` derives the runtime list from that file
and skips Slack, which keeps its own toolset function. If you add a field the
toolset needs, add it in the Code.gs `geMcpConfigJson` remote branch — never as
a lookup table inside `tools.py`.

### 9.4 Escaping notes for the DCR bash block

The whole flow is bash inside a JS template literal, so:

- Build every JSON body with `jq -n --arg`, never with `-d "{\"k\":\"v\"}"`.
  A single backslash inside a template literal is eaten before bash ever sees it.
- `tr -d '\n'` does not survive the template literal (the `\n` becomes a real
  newline). Use `openssl base64 -A` instead.
- Keep backticks out of anything spliced into the generated system instruction —
  section 2.2 explains why a stray backtick ends the enclosing template literal,
  and the instruction text is not a heredoc, so nothing protects it.
  `remoteMcpSlug_`-derived text is safe by construction, but `mcp.description`
  comes from a probe and is stripped of quotes, backslashes and backticks before
  use.

### 9.5 The authorization code arrives percent-encoded

`sed -n 's/.*[?&]code=\([^&]*\).*/\1/p'` pulls the code straight out of the
redirect URL, so it is still percent-encoded. Notion's codes contain `:`, which
shows up as `%3A`. Handing that to `curl --data-urlencode` encodes it a second
time (`%253A`) and the token endpoint answers
`invalid_grant / Invalid authorization code format`. Decode with
`urllib.parse.unquote` before the exchange. The Slack flow never hit this
because Slack codes are alphanumeric, but any new provider might.

The paste step also accepts a bare code, not just the full redirect URL: some
browser environments rewrite `https://localhost` in the address bar, so "copy
the whole URL" is not always possible.

### 9.6 Dynamically registered clients cannot be cleaned up

Notion returns `404` for `DELETE /register/<client_id>`, and this is normal for
RFC 7591 servers — registration is anonymous, so there is no credential that
authorizes deletion. Every setup run therefore leaves an orphaned client
registration behind. The cleanup script cannot fix this and says so, pointing
the user at the vendor's connected-apps settings to revoke access. Do not add a
"delete the client" step that silently no-ops.

### 9.7 `_ensure_types` must only recurse into subschema positions

`agent.py` monkey-patches ADK's `_dereference_schema` with
`_safe_dereference_schema`, whose `_ensure_types` walker repairs MCP input
schemas Gemini would otherwise reject. The recursion step used to be:

```python
for k, v in list(node.items()):
    if isinstance(v, dict):
        node[k] = _ensure_types(v)
```

That walks the value of the `properties` **keyword** — a name-to-schema map — as
if the map itself were a schema node. It usually looks harmless, because a map
of schemas and a schema both recurse into dicts. It stops being harmless the
moment a tool declares a property whose *name* collides with a JSON Schema
keyword:

- A property literally named `properties` (Notion `create-pages`, `update-page`)
  makes the map look like a node with a `properties` keyword. The shorthand
  fixup then iterates the real subschema's own entries as if they were
  properties, and rewrites its `"type": "object"` and `"description": "..."`
  **strings** into `{"type": "object"}` / `{"type": "<the description>"}` dicts.
- The trailing type inference fires on the map too (`"properties" in node` →
  `node["type"] = "object"`), injecting a phantom property named `type` into
  every object that has properties. Seen on `create-database` and
  `update-data-source`.

The corrupted declaration fails `_ExtendedJSONSchema.model_validate` inside
`_to_gemini_schema`, which raises during `_preprocess_async` — before the model
is ever called. ADK surfaces it as `DynamicNodeFailError: Dynamic node
root_agent failed`, the turn produces no event at all, and Gemini Enterprise
shows the user "User action triggered." followed by silence. There is no
`MALFORMED`, no retry, no partial text: an empty turn plus a pydantic
`ValidationError` in the Cloud Run log is the signature.

Recurse only into positions that actually hold schemas — `properties` / `$defs`
/ `definitions` / `patternProperties` values, `items` / `additionalProperties` /
`propertyNames` / `not` / `contains`, and the `anyOf` / `oneOf` / `allOf` /
`prefixItems` lists. Note this is a *generic* bug, not a Notion one; `items`,
`enum` and `default` are equally plausible property names and would have tripped
the type inference the same way.

Regression check before touching this function: run every tool schema from the
target MCP server through `_to_gemini_schema` with the patch applied, and diff
old-versus-new output on schemas that exercise `allOf` merging, 2-variant
`anyOf`, rich (3+ object variant) `anyOf`, and `$ref` cycles — those four paths
are what the walker exists for and must not change.
