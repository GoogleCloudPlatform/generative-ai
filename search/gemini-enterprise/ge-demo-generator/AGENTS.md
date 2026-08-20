# AGENTS.md — AI Agent Development Guide for Gemini Enterprise Demo Generator

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
  ├─ adk_agent/app/examples/0.9/*.json A2UI v0.9 few-shot examples
  │                                    (the composite catalog itself is fetched
  │                                     into adk_agent/app/catalogs/ at setup time)
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
`resolveOutputLanguage_()` accepts every vocabulary the UI has to hand
(Template Hub codes like `en`, research names like `Deutsch`, and since v11.58
`custom:<name>` for a language the user typed into a free-text box) and returns
`''` for anything else, which leaves the caller on a detection-only fallback.

**Free-text languages (v11.58, both selectors in v11.59).** Nothing but the
model does the translating, so a selector's list is a short list, not a limit —
`Other language...` reveals an input and the typed name travels as
`custom:<name>`. The list is only there to save typing, which is why the entries
added in v11.58 (Malay, Indonesian, Thai, Vietnamese, Filipino, Hindi, Arabic,
Turkish, Polish) are a convenience rather than a capability change. The Template
Hub got this first; v11.59 gave the customer-domain research selector the same
list and the same free-text box, so `SUPPORTED_RESEARCH_LANGS_` now bounds only
what **auto-detect** may answer with. Three rules hold the free-text path
together:

- **Sanitize before the prompt, not after.** `sanitizeCustomLanguage_()` strips
  quoting/markup characters and rejects anything over 40 characters or 4 words:
  a language name is a couple of words, so a sentence arriving in that box is
  far likelier to be an injection attempt than a language. A rejected value
  returns `{success: false, error: 'Unrecognized language'}` so the UI can say
  so, rather than silently rendering English.
- **Look languages up with `hasOwnProperty`.** `TEMPLATE_LANGS_['constructor']`
  is a function, and a truthiness check would have stringified it straight into
  the prompt. The frontend's per-language cache has the same hazard and the same
  fix (`cachedTemplateHub()`).
- **A language that cannot round-trip is a language that gets lost.**
  `researchCompanyByDomain` returns `detectedLanguage` for the Magic Wand and
  `regenerateGoalForWorkflows` to reuse, so an unlisted answer (a typed
  override, or auto-detect replying `Norsk`) comes back as `custom:Norsk`.
  Returned bare, it resolves to `''` two calls later and the scenario quietly
  reverts to text detection — the failure shows up as an English optimize on a
  Thai research result, nowhere near the code that caused it.

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

The same rule has a runtime twin. Some turns are answered by the executor
WITHOUT running the agent -- the deterministic `Run in Background:` press, for
one -- so nothing in the reply matches the conversation language by itself.
`_localize_ui_strings` translates those fixed strings with a small model call,
and it needs a *language sample* to do it. The sample must come from the SAME
turn that answers. Sampling `_last_typed_user_text(session)` looks right and is
structurally empty here: the press always follows a plan card, and that card
turn short-circuits too, so ADK never appended the typed message to the session.
The sample is now the press payload's own scope text, which carries the user's
wording. Related: **every fail-open branch has to log.** The empty-sample early
return was the branch that actually fired in the first live test and it returned
English without a trace -- the only way to tell it apart from a successful no-op
was that the emit landed 1 ms after the call.

### 2.5 A2UI card delivery and press context

> These were found on A2UI v0.8 and are written in its vocabulary
> (`beginRendering`/`surfaceUpdate`/`sendText`). The lessons still hold; section
> 13 gives the v0.9 spelling of each protocol name.

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

**A clean dangling-ref check is not a clean render.** Live 2026-08-04, the model
emitted three suggestion chips whose `Button.child` ids it then defined as `Row`
components with an empty `explicitList`. Every reference resolved, so the
dangling-ref diagnostic stayed clean and the healer passed the payload straight
through; the client rendered three blank pills the user could press but not
read. Reference integrity is not the property worth checking -- *reachability*
is. `_a2ui_is_blank` walks a button's child subtree and returns True only when it
provably renders nothing (missing id, empty spec, empty `Text`, or a container
whose every child is blank); anything it does not recognise counts as
renderable, so `_heal_blank_buttons` can never erase a label it merely failed to
parse. The replacement label is taken from the button's own `sendText` literal --
model-written, therefore already in the conversation language (section 2.4).
Inventing "Option 1" would hardcode English into a non-English conversation. A
button with no text payload is left alone rather than guessed at.

**Injected system notes ride the user's own message part list.** Completed
background tasks are announced by appending a `SYSTEM NOTE (auto-generated;
the user did NOT type this): ...` part to the SAME message the user typed into
-- deliberately, for maximum salience to whichever agent answers the turn. Any
helper that joins the message's text parts therefore picks it up.
`_extract_user_text` did, so the pre-flight gate's scope became "the user's
sentence + the note + the first 400 chars of the finished report": the plan
card's editable *adjust your request* box rendered the raw note, and the `Run in
Background:` chip carried it forward as its `sendText`. A sibling helper
(`_last_typed_user_text`) had filtered `SYSTEM NOTE` parts for a long time,
which is exactly why this looked handled -- **a filter on one reader is not a
filter on the class.** When an injection targets the user's own message, audit
every function that reads `new_message.parts`.

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
  (after Cloud Run deploy + Gemini Enterprise registration: `create_managed_agent.py wait`
  polls readiness, `warmup_managed_agent.py` stores the environment id in
  Firestore `<demo>_managed_agent_state/current`). The A/B split hides the
  ~8-10 min agent creation behind the rest of the setup.
- **`enableWorkspaceAuth` (auth-only mode)**: sets up the Gemini
  Enterprise OAuth authorization WITHOUT the Developer-Preview Workspace MCP servers (no
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
- `python3 probe_wire.py --service <cloud-run-service>` — talk to a deployed
  agent the way Gemini Enterprise does and print the wire (extension echo,
  part kinds, `metadata.mimeType`, A2UI message keys). Reach for it the moment
  the logs are clean but the client renders nothing (see section 13.6).
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

## 10. Scale-to-zero (`--min-instances 0`)

An idle demo used to bill for a warm 8Gi/2vCPU instance around the clock. The
deploy defaults to `--min-instances 0 --max-instances 1`, with `MIN_INSTANCES=1`
exported before the setup script as the escape hatch for a live presentation.
Three pieces of runtime work make that safe; each removes something that
silently depended on "an instance is always there".

### 10.1 A localhost self-call cannot survive a scale-to-zero

Background work used to start a daemon thread that POSTed
`http://localhost:$PORT/execute_task` and disconnected after a 0.5s read
timeout. That transport can only reach an instance that is *already serving*, it
dies with the process, and it has no retry.

`tools._dispatch_worker` prefers **Cloud Tasks** and keeps the self-call only as
a fallback for demos whose queue could not be provisioned. Cloud Tasks holds the
request open for the whole run (so Cloud Run will not scale the instance down
mid-task), retries when the instance carrying it is recycled, and *wakes* a cold
service. Load-bearing constraints:

- **Never dial `SELF_URL` from inside the container.** The service runs with
  `--ingress internal`; a request that leaves via the public URL and re-enters
  is classified as external and rejected. Cloud Tasks is exempt for the same
  reason the existing Pub/Sub push subscription to `/execute_task` is — a
  same-project Google-managed caller.
- **`audience` is the bare service URL**, not the URL with the path. Cloud Run
  validates the OIDC token against the service.
- **`dispatch_deadline` must be 1800s**, matching the Cloud Run request timeout
  (and the Cloud Tasks maximum). The worker runs the task inline before
  responding; anything shorter makes Cloud Tasks abandon and retry a live run.
- **Enqueuing needs `iam.serviceAccounts.actAs`.** The runtime service account
  names *itself* in the `oidc_token`, so this is a resource-level
  `roles/iam.serviceAccountUser` self-binding on the SA — it cannot go through
  the project-level role grant. Missing it makes every enqueue fail and the demo
  silently drops to the self-call.
- **Cleanup PURGES the queue, it does not delete it.** Cloud Tasks tombstones a
  deleted queue name for 7 days and refuses to recreate it; a re-setup inside
  that window would silently downgrade the demo to the self-call. An empty queue
  costs nothing.

### 10.2 A heartbeat is what separates a duplicate from a recovery

Retries mean `/execute_task` can receive a second delivery for a task that is
already `working`. Re-running would duplicate the work and race two writers on
one doc; refusing forever would freeze the doc at `working` whenever the first
runner died. The runner writes `updated_at` at most every
`WORKER_HEARTBEAT_EVERY_S` (30s) from inside `_bg_consume`, and the guard uses
its age to choose.

The heartbeat alone is **not sufficient**, and this is the subtle part. If the
instance dies at t=100s, Cloud Tasks retries ~15s later while the heartbeat is
still only ~115s old — well inside the 600s stale window — so a purely
heartbeat-based guard would ack the recovery as a duplicate and lose the run.
The guard therefore also reads `X-CloudTasks-TaskRetryCount`: **Cloud Tasks
never retries an attempt that is still in flight**, so a non-zero count is
positive proof that the previous runner terminated, however fresh its last
heartbeat looks. The stale-heartbeat branch then only has to cover the localhost
fallback, which has no retries and leaves no other trace of a dead runner.

Duplicates are acked with 2xx on purpose — a 5xx would make Cloud Tasks retry a
perfectly healthy run.

A matching sweep in `_inject_completed_tasks` fails any `working` doc whose
heartbeat is older than `WORKER_ABANDON_AFTER_S` (default 1800s, the Cloud Run
request timeout, so nothing healthy is ever swept). Without it a run whose Cloud
Tasks retries were all exhausted sits at `working` forever and the in-flight
guard keeps telling the user the task "is already executing". Autonomous tickets
(`interaction_id`) are skipped — they have their own recovery path,
`_ma_recover_orphaned_task`.

### 10.3 `InMemorySessionService` dies with the instance

ADK keeps the whole conversation in the process. At min-instances 1 one warm
instance answered nearly every turn, so this was invisible; at 0, an idle gap
ends the process and the next message starts from a blank history mid-demo.

`fast_api_app.py` mirrors each turn's session into `{demo}_adk_sessions`
(gzipped `events` + `state`) in the `finally` of `_process_request`, and
`_process_request_body` rehydrates on an in-memory miss before creating a blank
session. The flush runs **inside the per-session lock**, so a concurrent turn
cannot interleave a half-written history, and it runs even when the turn failed
— a failed turn still moved the conversation forward.

Deliberate limits, do not "fix" these without thinking:

- **Only the conversation is persisted.** `_session_last_artifact` and
  `builtins._ws_session_tokens` are process-local by design: the token is
  re-sent on every request, and losing the regenerate cache costs one replay.
- **The OAuth token is stripped** from the persisted state
  (`_session_persistable_state` skips the `GEMINI_AUTHORIZATION_ID` key). It is
  short-lived and re-supplied per request; it has no business in Firestore.
- **The blob is stamped with the ADK version that wrote it** and discarded on
  mismatch. ADK owns the `Event` schema; feeding a blob from another version to
  `Event.model_validate` is not worth the crash.
- **Firestore caps a document at 1 MiB.** The flush halves the event list until
  the gzipped blob fits under 800 KB, and skips the write if it still does not.

### 10.4 Why `--max-instances 1`

The runtime still assumes single-instance process-local state —
`_get_session_lock`, `_session_last_artifact`, `builtins._ws_session_tokens`,
`_WORKER_SEMAPHORE`. Capping at 1 makes that assumption true. It also avoids a
hazard the Firestore mirror would *not* catch: with two instances, turn N+2 can
land on a warm instance whose in-memory session predates turn N+1, and a warm
hit never consults Firestore. One instance serves up to 80 concurrent requests,
so this is not a throughput ceiling at demo scale.

### 10.5 What genuinely regresses, and what cannot be tested

- **First message after an idle gap costs a cold start.** Measured after a ~17
  min idle: ~20s to "Application startup complete", 37s for the whole turn
  against 9–13s warm, so about +25s on that one message.
- **Autonomous tasks now usually outlive their instance.** The SSE monitor
  thread was always best-effort, but at min-instances 0 an idle service is torn
  down *on purpose*. Pull recovery (`_ma_recover_orphaned_task` from the
  persisted interaction) stops being a safety net and becomes the primary
  delivery path. It fires on the user's next turn, which is also when they would
  have seen the announcement anyway.
- **The takeover branch of section 10.2 has no on-demand trigger.** The obvious
  lever does not work: swapping revisions **drains** the old instance — Cloud
  Run waits for in-flight requests before sending SIGTERM, and `/execute_task`
  holds its request open for the entire run. Measured twice; firing the kill one
  second after the task started still lost the race, and the traffic switch took
  155s precisely because it spent 88s waiting for the request it was meant to
  interrupt. Two things follow. Instances are recycled by idle scale-down and
  infrastructure churn, **not by deploys**, so a rollout during a demo will not
  orphan a running task. And testing this path means faking the *state*, not the
  failure: plant a `working` execution doc with a heartbeat older than
  `_WORKER_HEARTBEAT_STALE_S` and deliver `/execute_task` for it. That writes
  synthetic documents into a live demo's Firestore, so it is a deliberate
  decision, not something to do casually while testing something else.

## 11. Autonomous delegation: what actually reaches the sandbox agent

Two failures found together while diagnosing one stuck ticket. The ticket froze
at `working`/52%, and finalizing it would have delivered nothing anyway.

### 11.1 A root-agent callback is not a per-turn hook

Section 10 promotes pull recovery (`_ma_recover_orphaned_task`) to the *primary*
delivery path for autonomous tasks: at `--min-instances 0` the SSE monitor
thread usually dies with its instance. That recovery needs a driver that runs
every turn, and `_inject_completed_tasks` — `root_agent`'s
`before_agent_callback` — is not one. ADK resumes a session directly into
whichever agent was active when it ended, so a turn that lands on a sticky
`deep_analysis_agent` never enters `root_agent.run_async`:

```
04:14:01  last monitor heartbeat (12s cadence)
04:14:12  Shutting down                     <- idle scale-down, monitor thread dies
04:47:36  Starting Agent: root_agent
04:47:36  Agent Name: deep_analysis_agent   (+34ms, no LLM call in between)
```

That 34 ms gap is ADK resumption, not a transfer. The interaction had already
completed server-side; the doc sat at `working`/52% for 96 minutes.

The selection effect is what makes this worse than a rare miss. A session
becomes sticky on `deep_analysis_agent` by running a heavy analysis — which is
also what precedes a delegation. **The sessions that create orphans are
disproportionately the sessions that cannot heal them.**

`tools._ma_sweep_orphaned_tasks` is now called from the A2A request entry in
`fast_api_app.py` via `asyncio.to_thread`, before the completed-task query so a
ticket finalized now is announced in the same turn. The callback keeps a copy as
a backstop for the non-A2A paths. The general form: **anything that must run
once per turn belongs at the request entry, not on an agent.** Agent callbacks
fire per *agent run*, and which agents run is a routing decision the framework
makes.

### 11.2 The MCP servers were never reaching the sandbox agent

`_ma_override_tools` attaches BigQuery / Firestore / Knowledge Catalog MCP
servers to every delegation, and the agent brief told the sandbox agent it had
"direct read access to the demo dataset". Probed live against `base_agent`
`antigravity-preview-05-2026`:

| probe | payload | model's tool list |
|---|---|---|
| per-turn override, MCP only | `tools:[bq, firestore, catalog]` | `google:browse, google:search, default_api:*` — no MCP |
| per-turn override, one tool | `tools:[google_search]` | unchanged: the agent's **full** registered set |
| agent-level registration | `mcp_server` in `agents.create` | stored fine; asked to call it, the model replies `NO_MCP_TOOL` |

Row 2 is the decisive one: sending a single tool did not narrow anything, so the
interactions `tools` override is **ignored outright**. Row 3 closes the escape
hatch — registering MCP on the agent resource is accepted by the API and still
never reaches the model.

So the sandbox agent has never had database access. Believing the brief, it went
looking for the access it had been promised, found `bq` on `PATH`, and spent an
entire run trying to authenticate it — `gcloud auth list`, a metadata-server
curl, a credential-file search, `sudo`. 133 steps, 3,743 output tokens, zero
deliverables, while the task message already carried every figure the deck
needed. The same pattern reproduces across demos.

Nothing logged a warning: the override is accepted with a 200. **An ignored
parameter and an obeyed one look identical from the caller.** The
discriminating test is not "did the call succeed" but "does removing something
change the outcome".

What the brief and the delegation tool now say:

- `DATA ACCESS` states the agent has no database access, names the dataset and
  collection only to say they are unreachable, and declares the task message's
  `INPUT DATA` block the only source of internal data — authoritative and
  sufficient, in the same words `BROWSER FINDINGS` has always used.
- The credential dead ends are named explicitly (`bq` / `gcloud` / `gsutil` are
  on `PATH` but unauthenticated; no ADC, no metadata server, no `sudo`). Stating
  the principle abstractly does not work; an agent with a shell will always find
  something plausible to try.
- Investigation is bounded to two failures, after which the agent builds from
  what it has and states the gap. Missing figures go in the report so the
  assistant can query them and re-delegate.
- `delegate_autonomous_task` tells the *root* agent the same thing, and
  `input_data` went from "Optional data to embed verbatim" to required whenever
  the task touches internal data.

`_ma_override_tools` still sends the MCP servers, documented as a no-op, so the
attachment starts working the day the API supports it.

### 11.3 Skill packs are mounted relative to the working directory

The env spec's `target` is `/.agent/skills`, and the brief repeated that path
verbatim. `find /.agent/skills -name SKILL.md` fails; `ls .agent/skills` from
`/workspace` succeeds. The agent-facing text now says
`/workspace/.agent/skills` and adds a "list it relative first, and build anyway
if there are none" hedge. Leave the env spec `target` alone — the platform
interprets it.

---

## 12. The domain-research 429 is a shared bucket, not a bug (v11.59)

Symptom: **Research failed: AI Search Error: { "error": { "code": 429,
"message": "Unable to submit request because you've reached the maximum number
of requests with search as tool you can make per day. Remove Google search tool
from"** — truncated mid-sentence, and reproducible on every retry.

Two grounded call sites can produce it, both sending `tools:
[{googleSearch:{}}]`: `researchCompanyByDomain()` and
`callVertexAIWithSearch()` (BigQuery public-dataset discovery).

**The cap is per project per day, not per user and not per token spend.** So on
a project shared by a team, a builder who has made zero requests all day can be
locked out by everyone else's traffic, and it comes back on its own at the
midnight US/Pacific reset. Verified 2026-08-17: the identical request (same
model, same `googleSearch` tool, same body) returned HTTP 200 against a
dedicated project while a shared one was 429ing, which rules out the request
shape, the model, and the code. The daily search cap is **not** visible in
`gcloud alpha services quota list` — the 373 `aiplatform.googleapis.com` quota
entries contain no per-day search metric — so do not go looking for a Cloud
Quotas override to raise. The lever is the `PROJECT_ID` Script Property.

The code lesson is about the error, not the quota: `describeVertexError_()` now
names the project, the reset, and the shared-bucket mechanic, and logs the full
body instead of `substring(0, 200)`. **A truncated upstream error reads as a bug
in your own app.** The old message cut off at "Remove Google search tool from",
which is advice this app cannot take — ungrounded research would invent the
company facts the feature exists to ground.

## 13. A2UI v0.8 → v0.9 and the composite catalog (v11.61)

Gemini Enterprise now speaks A2UI **v0.9**, which unlocks a Gemini
Enterprise-specific **composite catalog** (52 components) that v0.8's bundled
*basic* catalog (18 primitives) could not reach. This was a **hard cutover** —
there is no dual-version switch and no v0.8 code path left. Four things the
generator used to fake are now native:

| Faked on v0.8 | Native on v0.9 |
|---|---|
| Tables built from nested `Row`/`Column` of `Text` | `MaterialTable` / `GcbpTable` |
| Charts rendered as generated PNG images | `VegaChart` |
| Dashboards opened in a separate browser tab | `IFrameSrcdoc` (sandboxed, inline) |
| Long reports crammed into the chat stream | `Canvas` (resizable side panel) |

No dependency bump: the already-pinned `a2ui-agent-sdk` revision ships
everything v0.9 needs.

### 13.1 The protocol delta

| v0.8 | v0.9 |
|---|---|
| `{"beginRendering": {"surfaceId", "root": "root"}}` | `{"version":"v0.9","createSurface":{"surfaceId","catalogId"}}` — **no `root` key**; a component with `id == "root"` is required instead |
| `{"surfaceUpdate": {...}}` | `{"version":"v0.9","updateComponents":{...}}` |
| `{"dataModelUpdate":{"path","contents":[{"key","valueString"}]}}` | `{"version":"v0.9","updateDataModel":{"surfaceId","path","value": <plain JSON>}}` |
| `{"deleteSurface":{...}}` | same, but `version` is now **required** |
| `"component": {"Text": {…}}` (key wrapper) | `"component": "Text", …props` (flat discriminator) |
| `{"literalString": "x"}` | `"x"` (a `{"path": "/a"}` binding is unchanged) |
| `"children": {"explicitList": [...]}` | `"children": [...]` |
| `distribution` / `alignment` | `justify` / `align` |
| `"action": {"name":"sendText","context":[{"key","value"}]}` | `"action": {"event": {"name", "context": {…}}}` |
| press arrives as a **TextPart** | press arrives as a **DataPart** (13.4) |

**`"v0.9"` is not `VERSION_0_9`.** The wire value stamped on every message is
the string `"v0.9"`; the SDK constant `a2ui.schema.constants.VERSION_0_9` is
`"0.9"`. They are not interchangeable. `A2UI_CLIENT_MESSAGE_VERSION` in
`agent_template/adk_agent/app/part_converters.py` holds the wire spelling.

### 13.2 Catalog wiring — three sites that must agree

1. **The setup script** fetches the catalog into the build context and *fails
   the setup* if it is missing or unparseable
   (`adk_agent/app/catalogs/gemini_enterprise_composite_catalog.json`). A
   missing catalog is otherwise a fatal `A2uiSchemaManager` error three to five
   minutes later at Cloud Run start. The Dockerfile re-asserts it parses and
   has a `catalogId`.
2. **`agent.py` and `fast_api_app.py`** build byte-identical managers
   (`A2uiSchemaManager(version=VERSION_0_9, catalogs=[CatalogConfig.from_path(...)],
   schema_modifiers=[remove_strict_validation])`). They must match: the second
   one produces the selected catalog that the healer and the runtime validation
   gate read. `remove_strict_validation` is required — without it the composite
   catalog's `allOf` composition over-rejects.
3. **The agent card**: extension URI `.../a2a-extension/a2ui/v0.9`, with the
   catalog's own `catalogId` (the gstatic URL) advertised as a supported
   catalog and repeated on every `createSurface`.

**MIME**: `_build_a2ui_part` calls `create_a2ui_part(msg, version=VERSION_0_9)`.
The SDK maps every version in `("0.8", "0.9", "v0.8", "v0.9")` to
`application/json+a2ui` and everything else to `application/a2ui+json`. The
constant names read backwards (`DEPRECATED_A2UI_MIME_TYPE` vs `A2UI_MIME_TYPE`)
— `application/a2ui+json` is the *future* spelling that no shipping client
reads yet. Dropping the kwarg degrades every card to plain text with a
completely clean log. The Dockerfile `RUN` and `canary.py` both assert the
resulting MIME.

### 13.3 Only 18 components are strict — the rest of the healer is migration

`remove_strict_validation` deletes `additionalProperties: false` but leaves
`unevaluatedProperties: false`, which marks exactly the 18 basic v0.9
primitives. **Every `Material*` component is schema-open**, so the unknown-property
pruner can only ever fire on a basic component, and for Material components the
healer's job is **shape migration**, not pruning. Two migrations are
non-obvious, and both were found by feeding the healer real v0.8 payloads
offline rather than by reading the diff:

- **A v0.8 `Button` with a flat `label` must be promoted to `MaterialButton`,
  not pruned.** The *basic* v0.9 `Button` has no `label` at all and *requires*
  `child`, so pruning the label produced a childless `Button` that the gate
  rejected, taking the whole card with it.
- **`MultipleChoice`→`ChoicePicker` is more than a rename.** The selection
  binding moved `selections`→`value`, and `variant` swapped enums entirely:
  v0.8's `chips`/`dropdown` were presentation hints, v0.9's
  `multipleSelection`/`mutuallyExclusive` encode cardinality. Without both, the
  renamed component keeps a dead binding and an out-of-enum variant.

Prop signatures verified against the catalog, each contradicting a plausible
guess: **`MaterialSlider` has no `label`**; **`MaterialChips` has no `label`**;
`MaterialTable` requires `columns` (`{header, field}`) + `rows`; `MaterialCard`
requires `children`; `MaterialText.usageHint` is `h1..h5, caption, body,
subtitle1/2, body1/2` — **`title` is not in it**; basic `Button` requires
`child`; `MaterialIcon.icon` is a free-form Material Icons font name with **no
enum**, so the old icon allowlist is gone. A dangling child id does **not** fail
validation — the parser only enforces reachability from `root`; it renders as a
hole in the card.

### 13.4 The inbound press is a DataPart now — folded back to one shape

This is the only genuinely new code path. Gemini Enterprise returns a press as

```json
{"version": "v0.9", "action": {"name": "...", "surfaceId": "...",
 "sourceComponentId": "...", "timestamp": "...", "context": {"prompt": "...", ...}}}
```

The agents use ADK's `A2aAgentExecutor`, which maps parts 1:1 — an action
DataPart would otherwise reach the model as raw JSON. `a2ui_client_action()`
recognises it in `convert_a2a_part_to_genai_part`, and
`a2ui_action_to_user_action()` folds it into the **existing**
`{"userAction": {...}}` text envelope. **Converting at the edge instead of
teaching each consumer a second dialect** is the load-bearing decision: the
pre-flight gate, the briefing-answer harvester and the duplicate-press dedup all
keep working unchanged. Presses are matched on the stable event name first
(`preflight_confirm*`, `autonomous_start*`) with the text path as a fallback;
per section 2.5, never gate a handler on a decorative context key.

**`context.prompt` is the user's chat message.** Gemini Enterprise renders that
literal string as what the user "said". Omit it and the user sees "User action
triggered." Corollary: **encode intent in the event `name` too**, never only in
the context — a name survives a model that forgets to bind a context value.

### 13.5 Verification order (all four are cheap; do not skip them)

1. `node --check` on a `.js` copy of Code.gs — the template-literal scan of
   section 2. **A bare backtick inside generated Python shreds the heredoc**;
   several crept in during this migration and most of them happened to
   *balance*, so they parsed and would have failed only at runtime.
2. `python3 validate_examples.py` — every example JSON parses, every template
   Python file compiles, and no surface sends one prompt from two presses.
3. **Offline protocol harness** — push each *server-authored* card (pre-flight,
   autonomous briefing, suggestion chips, `deleteSurface`) through
   `A2uiStreamParser(catalog=...).process_chunk('<a2ui-json>' + json + '</a2ui-json>')`.
   That is the identical gate the runtime applies, and it covers the cards
   `validate_examples.py` cannot see because they are built in Python. Write
   negative controls too — a harness that accepts v0.8 keys is not testing
   anything.
4. **Feed the healer v0.8 input** and assert the healed result passes the real
   gate.

### 13.6 Six live-deploy failures the offline gates could not see

None of these is a property of any card the generator authors.

**(a) The `MaterialTabs` reachability shim must be installed in `agent.py`, not
only where the healer lives.** `agent.py` runs
`generate_system_prompt(validate_examples=True)` at IMPORT time, and
`adk_agent/app/__init__.py` imports it before `fast_api_app.py` — so a shim that
only exists next to the runtime gate installs too late, and any tabbed example
kills the container at startup: `Component 'afterContent' is not reachable from
'root'`. Meta-lesson: `validate_examples.py` had the shim while the runtime did
not, making the **offline gate more permissive than production** — exactly
backwards. When a validator needs a patch to pass, first prove the runtime
applies the same patch on the same code path, in import order.

**(b) A plain-string ADK instruction is a TEMPLATE, and the catalog contains
`{expression}`.** ADK's `inject_session_state` raises `KeyError: Context
variable not found` for any brace-wrapped identifier not in session state. The
composite catalog's dynamic-string documentation contains a literal
`` `${expression}` `` in a component description; once
`generate_system_prompt(include_schema=True)` embeds the catalog into the
instruction, **every turn dies before the model runs**. The fix is
`bypass_state_injection`: pass an `InstructionProvider` (callable) instead of a
string. Never hand ADK a string instruction that embeds third-party text
(catalog, tool descriptions, fetched docs) — you do not control its braces, and
the catalog is re-fetched at every setup, so a token can appear upstream at any
time.

**(c) v0.9 A2UI parts are ignored without the extension-activation echo.** A
perfect turn server-side — `text`, `createSurface`, `updateComponents`,
gate-clean, correct agent card — rendered as text-only. Per the A2A extension
protocol, the client sends the extension URI in the `X-A2A-Extensions` REQUEST
header and treats the extension as INACTIVE unless the server echoes it in the
RESPONSE header. The v0.8 client rendered cards without the echo; the v0.9
client does not. The SDK's own mechanism (`RequestContext.add_activated_extension`)
**cannot work on the `message/stream` path**: `jsonrpc_app._create_response`
builds the SSE response headers BEFORE the agent executor has run, so
executor-side activation echoes only on non-streaming `message/send`. The fix is
`A2uiExtensionEchoMiddleware` in `fast_api_app.py`, which echoes on both paths
and logs `[a2ui_ext]`.

**(d) The A2UI version is read from the REGISTERED inline agent card, not the
live one.** With the echo in place the log showed `requested=...a2ui/v0.8`. The
version in `X-A2A-Extensions` comes from the `jsonAgentCard` embedded in the
Discovery Engine agent registration, **not** from
`/.well-known/agent-card.json`, which is never re-fetched. Rule: **the agent
card exists in two places; any capability change must touch both.** The
registration is idempotent-overwrite, so re-running the setup script propagates
the fix.

> Corollary: **"re-run the setup script" means REGENERATE it first.** The script
> is a self-contained artifact frozen at download time. Re-running an
> already-downloaded `.sh` re-applies the *old* card and looks exactly like the
> fix not working (registration `updateTime` advances, content does not).
> Diagnose by reading `a2aAgentDefinition.jsonAgentCard` back from the API
> rather than trusting that the script ran.

**(e) The renderer reads `application/json+a2ui`, the MIME the SDK calls
DEPRECATED.** With the extension negotiated end to end the cards *still* did not
render. Everything observable server-side was clean, so the next step was to
read the wire rather than the logs: `probe_wire.py` sends a real `message/stream`
POST carrying the client's own `X-A2A-Extensions` header and dumps
`metadata.mimeType` for every part. It showed `application/a2ui+json` — the
value the migration deliberately chose, because `A2UI_MIME_TYPE` sounds current
and `DEPRECATED_A2UI_MIME_TYPE` sounds obsolete. The names are aspirational.
Two lessons: **when a symbol's name and its behaviour disagree, believe the
reference implementation**, and **when the server logs are clean but the client
shows nothing, stop reading logs and read the wire.**

**(f) `A2uiStreamParserV09` bleeds one surface's components into the next.**
Live symptom: pressing *any* Next Actions chip sent the *first* chip's prompt.
`probe_wire.py` showed the turn's artifact carrying the card's 24 components a
second time under the suggestions surface. `_seen_components` in the SDK parser
is a **parser-lifetime cache keyed by component id**, but component ids are
surface-scoped and v0.9 requires every surface's root to be literally `root`, so
the second surface of a turn is filled by walking the topology from the *first*
card's `root`. Fixed in `fast_api_app.py` by giving each surface its own
component cache, swapped in the `surface_id` setter — the one choke point both
`_handle_complete_object` and `_sniff_metadata` assign through.

Two traps here, and the second cost the whole first day of the hunt:

- **`A2uiStreamParser(catalog=None)` silently returns the v0.8 parser.** The
  class is a factory: `__new__` dispatches on `catalog.version` and falls
  through to `A2uiStreamParserV08` for anything that is not `VERSION_0_9`,
  including no catalog at all. Six offline reproductions came back clean because
  all six were exercising v0.8 code. Any repro of parser behaviour must assert
  `type(parser).__name__ == 'A2uiStreamParserV09'` before it is worth anything.
- **The SDK's own over-yield guard is v0.8-only.** `process_chunk` dedupes
  repeated updates per surface by looking for the key `surfaceUpdate`, which no
  longer exists under v0.9.

**One press, one prompt.** The other half of that report was
`examples/0.9/suggestion_chips.json` teaching a single `MaterialChips` with
three `options` behind one `action`. `MaterialChips` carries ONE action for ALL
of its options, so it structurally cannot give each chip its own prompt —
whichever chip the user presses, the client sends that one action's prompt. A
navigation chip bar must be a `MaterialRow` of `MaterialButton`s;
`MaterialChips` stays correct for *bound selection* inside a form, where the
value flows through the data model rather than the action. No schema can express
this, so `validate_examples.py` checks it directly.
