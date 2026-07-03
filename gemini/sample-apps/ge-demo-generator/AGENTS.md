# AGENTS.md — AI Agent Development Guide for GE Demo Generator

> **Purpose**: Project-specific knowledge for AI coding agents (Antigravity, Cursor, Copilot, etc.)
> working on `Code.gs`. This document captures hard-won lessons from production escaping bugs,
> syntax errors, and architectural patterns unique to this codebase.

---

## 1. Architecture: Multi-Layer Code Generation

`Code.gs` is a Google Apps Script (JavaScript) file that **generates bash setup scripts**,
which in turn **generate Python source files** via heredocs. This creates a multi-layer
code generation pipeline where escaping errors are the #1 source of production failures.

```
Layer 1: Code.gs (JavaScript / GAS runtime)
  ↓  JS template literals or string concatenation
Layer 2: Bash setup script (setup-demo-xxx.sh)
  ↓  Heredocs (quoted or unquoted)
Layer 3: Python source files (agent.py, fast_api_app.py, tools.py, etc.)
  ↓  Runtime string operations
Layer 4: LLM system instruction (consumed by Gemini models)
```

### Viewer Escaping Chain (DIFFERENT from above!)

The Data Viewer template (`viewer_app/main.py`) has a **distinct 4-layer chain**
where Layer 3 is a Python triple-quoted string (`"""`) serving HTML, and Layer 4
is browser JavaScript — NOT an LLM instruction.

```
Layer 1: Code.gs (JavaScript / GAS runtime)
  ↓  JS template literal processes \\ → \
  ↓  (note: \n → actual newline!)
Layer 2: Bash quoted heredoc (<<'__VIEWER_MAIN__')
  ↓  Passes through verbatim (no expansion)
Layer 3: Python triple-quoted string (HTML_TEMPLATE = """...""")
  ↓  Python interprets \n → newline, \\ → \
  ↓  (This is the KEY difference from agent heredocs!)
Layer 4: Browser JavaScript execution
  ↓  JS interprets \n in string literals as newline
```

> [!CAUTION]
> The Python `"""` layer is an EXTRA escaping step. In agent heredocs (e.g.,
> `__AGENT_EOF__`), the Python file IS the final destination — Python runtime
> interprets `\n` directly. In the Viewer, Python `"""` renders HTML, and
> the **browser** must see `\n` (literal backslash + n) in the JS source.
> This means you need **4 backslashes** in Code.gs for the Viewer, vs **2**
> for agent heredocs.

### Key File Locations in Code.gs

| Heredoc | Delimiter | Type | Line Range (approx) | Generates |
|---------|-----------|------|---------------------|-----------|
| `.env` | `__ENV_EOF__` | Unquoted | ~L3095 | Runtime environment variables |
| `tools.py` | `__TOOLS_EOF__` | Quoted (`'...'`) | ~L3134-3864 | MCP toolset factories |
| `agent.py` | `__AGENT_EOF__` | Quoted (`'...'`) | ~L5236-5755 | Agent definitions |
| `part_converters.py` | `__PART_CONVERTERS_EOF__` | Quoted | ~L5755-6095 | A2A↔GenAI converters |
| `fast_api_app.py` | `__FAST_API_EOF__` | Quoted (`'...'`) | ~L6107-6993 | A2A server + event loop |
| `viewer_app/main.py` | `__VIEWER_MAIN__` | Quoted (`'...'`) | ~L1841-2420 | Data Viewer Flask app (HTML + JS) |

> [!IMPORTANT]
> Line numbers shift frequently as the file evolves (~8300+ lines). Use `grep` to find
> the actual heredoc boundaries before editing.

---

## 2. Escaping Rules — MANDATORY Reading Before Any Edit

### 2.1 The Golden Rules

1. **NEVER use `\n` in a Python string literal inside a quoted heredoc.** Even though
   `cat <<'EOF'` suppresses shell expansion, the backslash-n sequence (`0x5c 0x6e`)
   causes Python `SyntaxError: unterminated string literal` when the file is written.
   **Use `chr(10)` instead.**

2. **NEVER use f-strings in Python code inside heredocs that also contain JS template
   literal expressions.** The `{variable}` syntax conflicts between Python f-strings
   and JS `${expression}`. **Use string concatenation (`+`) instead.**

3. **NEVER use `$` in Python code inside an UNQUOTED heredoc.** It will be interpreted
   as a shell variable. Quoted heredocs (`'EOF'`) are safe from `$` expansion, but
   unquoted heredocs are not.

4. **Count your backslash layers before writing.** Each layer doubles the backslashes.

5. **For bash line continuation (`\` + newline) in a JS template literal, use `\\` (two
   backslashes), NOT `\\\\` (four).** JS template literal `\\` → single `\` in output →
   valid bash line continuation. Four backslashes produce `\\` in the output, which bash
   interprets as a literal backslash, not a line continuation.

6. **`$()` in a JS template literal does NOT need escaping.** JS only interpolates `${}`.
   `$(command)` is passed through verbatim to the output. Do NOT write `\$()` — that
   produces a literal `\$` in bash, which prevents command substitution.

7. **NEVER use `{variable_name}` or `{{variable_name}}` in agent system instructions
   (base_instruction text).** ADK's `instructions_utils.inject_session_state` uses the
   regex `r'{+[^{}]*}+'` which matches **one or more** opening braces + content + **one
   or more** closing braces. Both `{var}` and `{{var}}` are matched and resolved against
   session state, causing `KeyError` at runtime. **Use `<variable_name>` or
   `[VARIABLE_NAME]` instead.**

8. **NEVER use backtick triplets (` ``` `) anywhere in Code.gs, including inside
   heredoc content, comments, or string literals.** The GAS script editor parses the
   entire file as JavaScript. Backtick triplets are interpreted as JS template literal
   delimiters, causing `SyntaxError: Unexpected identifier` on whatever follows.
   **Use `chr(96) * 3` in Python code to construct the backtick fence dynamically.**

9. **In the Data Viewer template (`__VIEWER_MAIN__`), use `\\\\n` (4 backslashes + n)
   for JS newlines, NOT `\\n` (2 backslashes + n).** The Viewer has an extra Python
   `"""` layer that agent heredocs don't have. 2 backslashes produce `\n` in the
   Python file, which Python `"""` interprets as a real newline (0x0a), breaking the
   browser's JS string literal. 4 backslashes produce `\\n` in the Python file,
   which Python renders as `\n` (literal characters), letting the browser JS
   correctly interpret it as a newline escape.
   **Alternatively, avoid `\n` entirely — use HTML structure (`<div>`) instead of
   string concatenation with newlines.**

10. **ALWAYS verify which JS template conditional block you are inside before inserting
    code.** Conditional blocks (`${ flag ? \`...\` : '' }`) can span hundreds of lines.
    Feature-independent code (Firestore init, common imports, shared utilities) must
    NEVER be placed inside a feature-flag conditional block. See **Section 10** for
    detection commands and incident history.

11. **NEVER use bare double quotes (`'"'`) in Python string literals inside heredoc
    content that is wrapped in a JS template literal.** The GAS JavaScript parser
    processes the entire file and can misinterpret quote nesting, causing
    `SyntaxError: Unexpected string`. **Use `chr(34)` instead.**
    Example: `_text.strip('"')` → `_text.strip(chr(34))`.

12. **NEVER use `\n` in Python COMMENTS inside a JS template literal heredoc.** The
    `\n` is processed by the JS template literal layer BEFORE it reaches the heredoc,
    producing a real newline (0x0a). This splits the comment across lines. Content
    after the newline has no `#` prefix and is parsed as executable Python — causing
    `SyntaxError` if it contains emoji or other invalid syntax. **Use plain-text
    descriptions instead of literal escape sequences in comments.**

13. **NEVER use unescaped single backticks (`` ` ``) inside JavaScript template literals in Code.gs.**
    `Code.gs` contains huge JS template literals that act as code generators (e.g., `getTechnicalInstruction_()`). Using raw backticks inside these blocks (for example, to highlight a word in a text description like `` `context` ``) will prematurely close the template literal, leading to compilation/clasp push failure: `SyntaxError: Unexpected identifier`.
    **Use plain text, quotes, or explicitly escape the backtick (`` \` ``) instead.**

### 2.2 Escaping by Heredoc Type

#### Quoted Heredoc (`cat <<'EOF'`)
- Shell does NOT expand `$`, `\`, or backticks
- Content is written **verbatim** to the target file
- ⚠️ BUT: If the heredoc content is inside a JS template literal, JS processes it first

#### Unquoted Heredoc (`cat <<EOF`)
- Shell DOES expand `$VAR`, `$(command)`, and backslash sequences
- `\n` becomes an actual newline, `\t` becomes a tab
- Use `\$` to write a literal `$` to the target file

### 2.3 Escaping Chain Examples

#### Example A: Newline character in Python string (inside quoted heredoc)

**WRONG** — causes `SyntaxError: unterminated string literal`:
```javascript
// In Code.gs, inside a <<'__FAST_API_EOF__' heredoc:
                              _fc_status_text = '\n'.join(_fc_lines)
```

**RIGHT** — shell-safe alternative:
```javascript
// In Code.gs, inside a <<'__FAST_API_EOF__' heredoc:
                              _fc_status_text = chr(10).join(_fc_lines)
```

> [!WARNING]
> This is the #1 most common bug in this codebase. It has caused **multiple production
> deployment failures**. The `\n` in `'\n'` is interpreted as a literal newline by some
> layer of the code generation pipeline, breaking the Python string literal across lines.

#### Example B: Newline in replace() (inside quoted heredoc)

**WRONG**:
```javascript
_sql[:200].replace('\n', ' ')
```

**RIGHT**:
```javascript
_sql[:200].replace(chr(10), ' ')
```

#### Example C: Python code that reads environment variables (inside quoted heredoc)

**SAFE** — no `$` or `{}` conflicts:
```javascript
// Inside <<'__AGENT_EOF__'
_viewer_url = os.environ.get("DATA_VIEWER_URL", "")
if _viewer_url:
    instruction += "URL: " + _viewer_url + "\\n"
```

> Note: `\\n` here (double-backslash-n) is correct — it's a JS escape that produces
> the literal characters `\n` in the bash script, which the quoted heredoc passes
> verbatim to Python, where `\n` is interpreted as a newline at runtime.

#### Example D: Shell variable in deployment commands (JS template literal)

```javascript
// In Code.gs (JS template literal for bash script):
deployCmd += `\nCR_ENV_VARS="${envVars.join(",")}"
if [ "\$VIEWER_DEPLOYED" = "true" ]; then
  CR_ENV_VARS="\$CR_ENV_VARS,DATA_VIEWER_URL=\$VIEWER_URL"
fi\n`;
```

Escaping chain:
- `${envVars.join(",")}` → JS interpolation at GAS runtime → baked-in string values
- `\$VIEWER_DEPLOYED` → `\$` prevents JS `${}` interpolation → literal `$` in bash → shell expands

#### Example E: Four-layer escaping for system instruction injection

```
Code.gs (JS):  "\\\\n\\\\n--- HEADER ---\\\\n"
    ↓ JS processes \\\\ → \\
Bash script:   "\\n\\n--- HEADER ---\\n"
    ↓ Quoted heredoc passes through
Python source: "\\n\\n--- HEADER ---\\n"
    ↓ Python runtime interprets \n
LLM sees:      (newline)(newline)--- HEADER ---(newline)
```

#### Example G: Regex patterns in Python raw strings (inside JS template literal + quoted heredoc)

Python `r'...'` raw strings do NOT process `\s` or `\n`, but the JS template literal
layer processes them BEFORE the content reaches the heredoc. In a JS template literal,
`\n` (single backslash) is interpreted as a newline character.

**WRONG** — JS interprets `\n` as newline, breaking the Python string literal:
```javascript
// In Code.gs, inside a JS template literal containing <<'__FAST_API_EOF__':
_pattern = _re.compile(r'(?:tool_code|python)\s*\n(.*?)')
```

Escaping chain: `\n` → JS produces newline char (0x0a) → heredoc writes 0x0a →
Python `r'...'` string literal is split across lines → `SyntaxError: unterminated string literal`

**RIGHT** — double backslashes survive JS processing:
```javascript
// In Code.gs:
_pattern = _re.compile(r'(?:tool_code|python)\\s*\\n(.*?)')
```

Escaping chain: `\\s` → JS produces `\s` → heredoc writes `\s` →
Python `r'...\s...'` → regex metacharacter for whitespace ✅

> [!WARNING]
> This is counter-intuitive because Python raw strings (`r'...'`) should preserve
> backslashes as-is. However, the JS template literal layer processes the content
> BEFORE it reaches the Python file, so JS escaping rules apply first.

#### Example H: Newline in JS string literal inside Data Viewer template

The Viewer template has an extra Python `"""` layer (see Section 1: Viewer Escaping
Chain). JS string literals containing `\n` must survive 4 layers.

**WRONG** — 2 backslashes: `SyntaxError: Invalid or unexpected token` in browser:
```javascript
// In Code.gs (JS template literal containing <<'__VIEWER_MAIN__' heredoc):
// Inside Python HTML_TEMPLATE = """...<script>...
body += '--- Description ---\\n' + text;
```

Escaping chain:
```
Code.gs:  \\n  (0x5c 0x5c 0x6e)
  ↓ JS template literal: \\ → \, n → n
bash:     \n   (0x5c 0x6e)
  ↓ Quoted heredoc: verbatim
Python:   \n   (0x5c 0x6e) inside """..."""
  ↓ Python runtime: \n → newline (0x0a)  ← BREAKS HERE
HTML:     actual newline in JS code → SyntaxError!
```

**RIGHT** — 4 backslashes:
```javascript
body += '--- Description ---\\\\n' + text;
```

Escaping chain:
```
Code.gs:  \\\\n  (0x5c 0x5c 0x5c 0x5c 0x6e)
  ↓ JS template literal: \\\\ → \\, n → n
bash:     \\n    (0x5c 0x5c 0x6e)
  ↓ Quoted heredoc: verbatim
Python:   \\n    (0x5c 0x5c 0x6e) inside """..."""
  ↓ Python runtime: \\ → \, n → n = literal \n (0x5c 0x6e)
HTML:     \n in JS source → browser interprets as newline ✅
```

**BEST** — avoid the problem entirely by using HTML structure:
```javascript
// Instead of '--- Description ---\\\\n' + text
html += '<div class="detail-field">' + key + ': ' + val + '</div>';
```

> [!CAUTION]
> This is the most insidious escaping bug in this codebase because the 2-backslash
> fix (`\\n`) works correctly for ALL other heredocs (agent.py, fast_api_app.py,
> etc.) where the Python file is the final destination. Only the Viewer template,
> which wraps JS inside Python `"""` inside a heredoc, requires 4 backslashes.

#### Example I: `\n` in Python comments (inside JS template literal + quoted heredoc)

Python comments (`#`) only cover text up to the end of the line. If a comment
contains `\n` inside a JS template literal, JS converts it to a real newline,
splitting the comment across two lines. The second line has NO `#` prefix and is
parsed as executable Python.

**WRONG** — JS interprets `\n` as newline, breaking the comment:
```javascript
// In Code.gs, inside a JS template literal containing <<'__FAST_API_EOF__':
            #   "---\n### 💡 Next Actions"
            #   "---\n\n💡 Next Actions"  (no # marks)
```

After JS processing, the Python file contains:
```python
            #   "---
### 💡 Next Actions"
            #   "---

💡 Next Actions"  (no # marks)
```

The lines starting with `💡` have no `#` prefix → `SyntaxError: invalid character '💡'`.

**RIGHT** — use plain-text descriptions instead of literal escape sequences:
```javascript
            #   "---" + newline + "### Next Actions"
            #   "---" + newlines + "Next Actions"  (no hash marks)
```

> [!WARNING]
> This is easy to overlook because comments feel "safe" — but the JS template literal
> layer processes ALL content (including comments) before it reaches the heredoc.
> Rule #1 (no `\n` in string literals) applies equally to comments.

#### Example J: Checking for triple-backtick code blocks inside Python code in Code.gs

When writing Python code inside a quoted heredoc (e.g., `__AGENT_EOF__`), you may need to search string content for markdown code blocks (such as ````python``). Writing literal backticks inside `Code.gs` is strictly forbidden by Rule 8.

**WRONG** — causes `SyntaxError: Unexpected identifier 'python'` during Clasp push:
```javascript
# In Code.gs, inside a <<'__AGENT_EOF__' heredoc:
if "```python" in part.text:
    return None
```

**RIGHT** — construct the backtick fence dynamically using character codes:
```javascript
# In Code.gs:
if (chr(96) * 3 + "python") in part.text:
    return None
```


### 2.4 ADK Instruction Template Engine Hazard

ADK's `instructions_utils.inject_session_state()` (called automatically before every
LLM request) scans the agent's `instruction` text with regex `r'{+[^{}]*}+'` and tries
to substitute matches from session state. If the variable is not found, it raises
`KeyError: 'Context variable not found: ...'`, which crashes the entire request.

**Critical details:**
- The `{+` quantifier means `{var}`, `{{var}}`, `{{{var}}}` are ALL matched
- Double-bracing (`{{var}}`) does NOT escape — it is still caught by the regex
- This applies to the `instruction` field of `LlmAgent` (and sub-agents)
- `[BRACKET]` and `<angle_bracket>` notations are safe

#### Example F: Placeholder in agent instruction (system prompt)

**WRONG** — causes `KeyError: 'Context variable not found: document_id'`:
```python
# In base_instruction (inside <<'__AGENT_EOF__' heredoc):
# Path: projects/.../documents/collection/{document_id}
```

**STILL WRONG** — `{{` is also matched by `{+`:
```python
# Path: projects/.../documents/collection/{{document_id}}
```

**RIGHT** — angle brackets are not interpreted by ADK:
```python
# Path: projects/.../documents/collection/<document_id>
```

#### Example K: Loop placeholders in A2UI instructions (system prompt)

**WRONG** — `{i}` is matched by ADK's template engine, causing `KeyError: 'Context variable not found: i'` at runtime:
```python
# In getTechnicalInstruction_ (inside Code.gs):
# "...bound to /form/item_{i}_name"
```

**RIGHT** — use plain `i` or brackets `[i]` to avoid engine matching:
```python
# In getTechnicalInstruction_:
# "...bound to /form/item_i_name"
```

### 2.5 Verification Checklist

Before submitting any change that touches Python code inside heredocs:

- [ ] Search for `'\n'` or `"\n"` (single-backslash-n in string literals) → replace with `chr(10)`
- [ ] Search for `'\t'` or `"\t"` → replace with `chr(9)` if inside a heredoc
- [ ] Search for `'\r'` or `"\r"` → replace with `chr(13)` if inside a heredoc
- [ ] Confirm no f-strings use `{` that could conflict with JS `${}`
- [ ] Confirm `$` usage: quoted heredoc = safe; unquoted heredoc = needs `\$`
- [ ] Search for `{word}` or `{i}` loop placeholders in agent `instruction` text (including `getTechnicalInstruction_`) → replace with `<word>`, `[WORD]`, or plain `i` / `[i]`
- [ ] Search for backtick triplets (` ``` `) → replace with `chr(96) * 3` in Python code
- [ ] Check regex patterns in raw strings (`r'...'`): `\s`, `\n`, `\t` need `\\s`, `\\n`, `\\t` for JS layer
- [ ] **Viewer template (`__VIEWER_MAIN__`)**: Any JS `\n` in string literals needs `\\\\n` (4 backslashes) due to the extra Python `"""` layer
- [ ] **Conditional block check**: Verify new code is not accidentally inside a `${ flag ? ... }` block (see Section 10)
- [ ] Search for `'"'` or `strip('"')` in Python code inside heredocs → replace `'"'` with `chr(34)`
- [ ] **Comments check**: Search for `\n`, `\t`, `\s` inside Python comments (`#`) — they are processed by JS just like code
- [ ] Run hex verification: `sed -n 'Lp' Code.gs | xxd` to check actual bytes

#### Automated Scan Command

Run this to find potential escaping issues in all Python heredoc blocks:

```bash
python3 -c "
with open('Code.gs', 'rb') as f:
    lines = f.readlines()
# Check for single-backslash-n (0x5c 0x6e) NOT preceded by another backslash
for i, line in enumerate(lines):
    for j in range(len(line)-1):
        if line[j] == 0x5c and line[j+1] in (0x6e, 0x74, 0x72):
            if j == 0 or line[j-1] != 0x5c:
                # Check if inside a Python string context (rough heuristic)
                text = line.decode('utf-8', errors='replace')
                if \"'\" in text or '\"' in text:
                    print(f'L{i+1}: {text.rstrip()}')
"
```

---

## 3. Dockerfile Code Generation Patterns

### 3.1 File Generation Inside Docker Images

Files that need to exist inside the Docker image (e.g., `_run.py` for MCP launchers)
**cannot** be created via local heredocs if the target directory only exists inside
the Docker image (created by `RUN git clone`).

**WRONG** — `custom_mcp_0/` doesn't exist locally:
```bash
cat <<'EOF' > custom_mcp_0/_run.py
import asyncio
...
EOF
```

**WRONG** — `printf` breaks due to multi-layer escaping:
```dockerfile
RUN printf 'import asyncio\nfrom...' > custom_mcp_0/_run.py
```

**RIGHT** — create locally, then COPY:
```bash
# In setup script (local filesystem):
cat <<'__RUN_PY_0_EOF__' > _run_0.py
import asyncio
from server import my_server
...
__RUN_PY_0_EOF__

# In Dockerfile:
COPY _run_0.py /app/custom_mcp_0/_run.py
```

### 3.2 Principle: Minimize Escaping Layers

When generating files that will end up inside Docker images:
1. **Prefer local heredoc + COPY** over `RUN printf` or `RUN echo`
2. **Prefer quoted heredocs** (`<<'EOF'`) to avoid shell expansion entirely
3. **Never use `.join('\\n')` in JS** to build Python code — the backslash-n
   will survive as literal characters, not actual newlines

---

## 4. Conditional Environment Variable Injection

When adding environment variables that depend on deployment success (e.g., `DATA_VIEWER_URL`):

### Pattern: Bash Variable Construction → `--set-env-vars`

```javascript
// In Code.gs JS template literal:
deployCmd += `\nCR_ENV_VARS="${envVars.join(",")}"
if [ "\$VIEWER_DEPLOYED" = "true" ]; then
  CR_ENV_VARS="\$CR_ENV_VARS,DATA_VIEWER_URL=\$VIEWER_URL"
fi\n`;
// Then use:
deployCmd += `--set-env-vars="\$CR_ENV_VARS"`;
```

**Key insight**: Build the env-vars string in a bash variable FIRST, then reference
it in the `gcloud` command. This avoids trying to conditionally modify a static
`--set-env-vars` flag.

---

## 5. Dynamic System Instruction Injection (agent.py)

When adding context-aware agent behavior that depends on environment variables:

### Pattern: Runtime String Concatenation (No f-strings)

```python
# Inside <<'__AGENT_EOF__' heredoc in Code.gs:
_viewer_url = os.environ.get("DATA_VIEWER_URL", "")
if _viewer_url:
    instruction += (
        "\\n\\n--- SECTION HEADER ---\\n"
        "Content: " + _viewer_url + "\\n"
        "More content.\\n"
        "--- END SECTION ---\\n"
    )
```

**Rules**:
1. Use `os.environ.get()` — no `$` characters that could conflict
2. Use string concatenation (`+`) — no f-strings that could conflict with JS `${}`
3. Use `\\n` (double-backslash) for newlines — JS `\\` → single `\` in bash → Python `\n`
4. Guard with `if _var:` — agent must remain completely unaware when the feature is absent

---

## 6. Common Pitfalls & Anti-Patterns

### ❌ Anti-Pattern: Background Process for Sequential Dependencies

If a downstream step needs the result of a deployment (e.g., a URL), do NOT deploy
in a background subshell:

```bash
# WRONG: URL is not available when needed later
(deploy_viewer) &
viewer_pid=$!
# ... later ...
wait $viewer_pid
VIEWER_URL=$(get_url)  # Race condition or ordering issues
```

```bash
# RIGHT: Sequential deployment guarantees URL availability
deploy_viewer
if [ $? -eq 0 ]; then
  VIEWER_URL=$(get_url)
  VIEWER_DEPLOYED=true
fi
```

### ❌ Anti-Pattern: Assuming `--ingress internal` Blocks All Traffic

`--ingress internal` allows traffic from within the same VPC/project,
including Gemini Enterprise A2A calls. Do NOT change to
`internal-and-cloud-load-balancing` without understanding the actual traffic path.
The agent has historically worked correctly with `internal`.

### ❌ Anti-Pattern: Multiple Iteration Fixes

If a fix requires understanding multi-layer escaping:
1. **Stop and trace the full chain** before writing code
2. Write the expected output at each layer
3. Verify with `xxd` hex dumps
4. Fix ALL occurrences at once, not one at a time

### ❌ Anti-Pattern: Python Fix Scripts with `\n` in Replacement Strings

When using a Python script to modify Code.gs (e.g., `content.replace(old, new)`),
be aware that Python's own string escaping applies to the replacement values:

```python
# WRONG — Python interprets \n as newline (0x0a), corrupting Code.gs:
new_code = "_re.compile(r'pattern\\\\s*\\\\n(.*?)')"  # \\\\n → \\ + newline!

# RIGHT — use raw bytes to avoid Python string escaping:
old = b"pattern\x5c\x73"   # literal bytes: \ s
new = b"pattern\x5c\x5c\x73"  # literal bytes: \\ s
content = content.replace(old, new)
```

**Rule**: When modifying Code.gs programmatically, always operate on **raw bytes**
(`rb`/`wb` mode) to prevent the fix script's own escaping from interfering.

---

## 7. Testing & Verification

### 7.1 Pre-Deploy Checks

1. **Syntax scan**: Run the automated scan command from Section 2.4
2. **Hex verification**: For any modified line in a heredoc, verify with `sed -n 'Lp' Code.gs | xxd`
3. **Git diff review**: `git diff Code.gs` — check every `\n` and `$` in the diff

### 7.2 Post-Deploy Checks

1. **Cloud Run logs**: Check for `SyntaxError` in startup logs
2. **MCP sidecar health**: Verify `✅ N/N MCP sidecars ready` message
3. **Agent card**: Hit `/.well-known/agent.json` to verify the service started
4. **Thinking accordion**: Verify model name display (`🧠 Model: ...`)

---

## 8. Reference: Heredoc Boundary Discovery

To find all heredoc boundaries in Code.gs:

```bash
grep -n "EOF\|__.*EOF" Code.gs | head -60
```

To check which heredoc a specific line belongs to:

```bash
# Find the nearest heredoc start BEFORE line N:
awk 'NR<=N && /<<.*EOF/' Code.gs | tail -1
```

---

## 9. Changelog of Escaping Incidents

| Date | Issue | Root Cause | Fix |
|------|-------|------------|-----|
| 2026-05-06 | `_run.py` `No such file or directory` | Local heredoc targeting Docker-only directory | Move to local file + `COPY` |
| 2026-05-06 | `_run.py` literal `\n` characters | `printf` multi-layer escaping | Replace `printf` with heredoc + `COPY` |
| 2026-05-07 | `SyntaxError: unterminated string literal` (L462) | `'\n'` in `.replace()` inside `__FAST_API_EOF__` | `chr(10)` |
| 2026-05-07 | `SyntaxError: unterminated string literal` (L480) | `'\n'.join()` inside `__FAST_API_EOF__` | `chr(10).join()` |
| 2026-05-07 | Data Viewer URL not propagated | Background deploy → race condition | Sequential deploy + conditional env-var injection |
| 2026-05-08 | `gcloud functions deploy` args treated as separate commands | `\\\\` (4 backslashes) in JS template literal → `\\` in bash (not a valid line continuation) | `\\` (2 backslashes) → JS produces `\` → valid bash line continuation |
| 2026-05-08 | `syntax error near unexpected token '('` | `\\$()` in JS template literal → `\$()` in bash (literal `$`, not command substitution) | `$()` directly — JS only interpolates `${}`, not `$()` |
| 2026-05-08 | `KeyError: 'Context variable not found: document_id'` | `{document_id}` in agent instruction matched by ADK template regex `r'{+[^{}]*}+'` | Replace `{document_id}` with `<document_id>` — angle brackets avoid ADK template engine |
| 2026-05-08 | Same KeyError persists after `{{document_id}}` fix | ADK regex `{+` matches **any** number of opening braces, so `{{var}}` is still caught | Confirmed: only non-brace notation (`<>`, `[]`) is safe |
| 2026-05-10 | `SyntaxError: Unexpected identifier 'tool_code'` (L6751) | Backtick triplets (` ``` `) in Python regex patterns and comments inside heredoc interpreted as JS template literals by GAS parser | Replace ` ``` ` with `chr(96) * 3` in Python; remove backtick triplets from comments |
| 2026-05-10 | `SyntaxError: unterminated string literal` (L301 in deployed fast_api_app.py) | `\s` and `\n` in Python regex raw string inside JS template literal: JS interpreted `\n` as newline character (0x0a), splitting the string literal | Double backslashes: `\\s*\\n` — JS processes `\\` → `\`, producing `\s*\n` in the Python file |
| 2026-05-13 | `Firestore not available (client=False, ...)` — background task tools fail | Firestore client init code placed inside `${ enableWorkspaceMcp ? ... }` conditional block from first commit (`6e331c7`). When `enableWorkspaceMcp=false`, init code was never emitted, leaving `builtins._firestore_client` unset | Move Firestore init outside the conditional block; add AGENTS.md Section 10 and Golden Rule #10 |
| 2026-05-18 | `SyntaxError: Unexpected string` (L7293) | `strip('"')` in Python code inside `__AGENT_EOF__` heredoc — GAS JS parser misinterpreted the bare double quote in the Python string literal | Replace `'"'` with `chr(34)` — avoids GAS parser quote-nesting confusion |
| 2026-05-19 | `SyntaxError: invalid character '💡' (U+1F4A1)` (L917 in deployed fast_api_app.py) | `\n` in Python comments inside JS template literal: JS converted `\n` to real newline (0x0a), splitting the comment across lines. Second line had no `#` prefix, exposing `💡 Next Actions` as executable Python code | Replace literal `\n` sequences in comments with plain-text descriptions (e.g., `"---" + newline + "### Next Actions"`) |
| 2026-05-21 | `SyntaxError: Unexpected identifier 'python'` (L7259) | Backtick triplets (` ``` `) used in Python code literal inside heredoc broke JS template literal delimiter in Code.gs during clasp push | Replace with dynamic string construction (`(chr(96) * 3 + "python")`) |

---

## 10. JS Template Conditional Block Boundaries

### The Problem

Code.gs uses JS template literal conditional blocks (`${ flag ? \`...\` : '' }`) to
conditionally include large sections of generated Python/Bash code. These blocks can
span **hundreds of lines**, making it easy to accidentally insert feature-independent
code inside a conditional block.

### 10.1 Golden Rule (also listed as Rule #10 in Section 2.1)

**ALWAYS verify which conditional block you are inside before inserting code.**
Feature-independent code (e.g., Firestore init, common imports, shared utilities)
must NEVER be placed inside a feature-flag conditional block.

### 10.2 How to Check Your Location

Before inserting code at line N, run:

```bash
# Find all conditional block starts BEFORE line N:
awk 'NR<=N && /\$\{.*\?.*`/' Code.gs | tail -3

# Find all conditional block ends AFTER line N:
awk 'NR>=N && /` : .*\}/' Code.gs | head -3
```

If the nearest block start has no matching block end before your insertion point,
**you are inside a conditional block**.

### 10.3 Known Long Conditional Blocks

| Flag | Block Start (approx) | Block End (approx) | Span |
|------|---------------------|-------------------|------|
| `enableWorkspaceMcp` (tools.py) | ~L4146 | ~L4460 | ~314 lines |
| `enableWorkspaceMcp` (agent.py) | ~L6569 | ~L6772 | ~203 lines |

> [!IMPORTANT]
> Line numbers shift frequently. Always use `grep` to find actual boundaries.

### 10.4 Incident History

| Date | What Happened | Lines Affected |
|------|---------------|----------------|
| 2026-05-13 | Firestore client init placed inside `enableWorkspaceMcp` block. When flag=false, `builtins._firestore_client` was never set, breaking all background task tools. | L4148 (should have been before L4132) |
