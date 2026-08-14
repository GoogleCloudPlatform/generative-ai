# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Template-shell rendering: splice a model-written JS payload (PRISM_SPEC +
PRISM_SIM) into the fixed, hand-crafted HTML shell. This is the "fast" path —
the model writes ~2-4KB of sim logic instead of a full ~15KB document.
"""

import os
import re

from app.schemas import UIVerdict

MARKER = "/*__PRISM_FILL__*/"
SHELL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shell.html")

with open(SHELL_PATH, encoding="utf-8") as _fh:
    SHELL = _fh.read()


def _sanitize_fill(fill: str) -> str:
    """Strip markdown fences and neutralize any stray </script> in the payload."""
    s = (fill or "").strip()
    if s.startswith("```"):
        nl = s.find("\n")
        s = s[nl + 1 :] if nl != -1 else ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
        s = s.strip()
    return s.replace("</script>", "<\\/script>")


def assemble(fill: str) -> str:
    """Splice the model's JS payload into the shell (marker replaced once)."""
    return SHELL.replace(MARKER, _sanitize_fill(fill), 1)


# step(state, dt) {  — the opening; the body is then found by brace matching so
# a one-line `step(s,d){}` and a 20-line block are both handled exactly.
_STEP_OPEN_RE = re.compile(r"\bstep\s*\(\s*\w+\s*(?:,\s*\w+\s*)?\)\s*\{")
_COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def _step_body(fill: str) -> str | None:
    """Return step()'s body with comments stripped, or None if there is no step.

    Comments are stripped BEFORE the search and the search is scoped to the
    PRISM_SIM object: prose like "draw()/step() stay small" in a comment would
    otherwise match first and brace-match nonsense out of the following text.

    Brace-matched rather than regex-delimited, because the model writes step()
    both as a one-liner and as a multi-line block, and a length-based pattern
    reports a present-but-empty step as "missing" — a different, wrong hint.
    """
    src = _COMMENT_RE.sub("", fill or "")
    sim = src.find("PRISM_SIM")
    m = _STEP_OPEN_RE.search(src, sim if sim >= 0 else 0)
    if not m:
        return None
    depth, start = 1, m.end()
    i = start
    while i < len(src) and depth:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return (src[start : i - 1] if depth == 0 else src[start:]).strip()


def check_fill(fill: str) -> UIVerdict:
    """Template-mode verification: the payload must define both globals, look
    complete, and — critically — actually ANIMATE.

    The inertness checks exist because the common failure is not a crash: the
    model emits a gorgeous static scene with an empty `step(){}`, the shell
    autoplays it, and the user presses Play to no effect. That renders and
    passes every structural check, so without this it ships silently broken.
    """
    errors: list[str] = []
    s = fill or ""
    if len(s.strip()) < 40:
        errors.append("Fill payload too short.")
    if "PRISM_SPEC" not in s:
        errors.append("Missing PRISM_SPEC.")
    if "PRISM_SIM" not in s:
        errors.append("Missing PRISM_SIM.")
    # crude truncation check: roughly balanced braces
    if s.count("{") - s.count("}") not in (-1, 0, 1):
        errors.append("Unbalanced braces (payload likely truncated).")

    # --- the instrument must be alive -------------------------------------
    body = _step_body(s)
    if body is None:
        errors.append(
            "PRISM_SIM.step(state, dt) is missing — the instrument cannot animate."
        )
    elif not body:
        errors.append(
            "PRISM_SIM.step(state, dt) is empty — nothing advances, so Play does nothing. "
            "Advance a field you set in init() (e.g. state.phase += dt * speed) and loop it."
        )
    elif "state." not in body:
        errors.append(
            "PRISM_SIM.step(state, dt) never touches state — it cannot be advancing the sim."
        )
    # the sliders must drive the RUNNING sim, not just its initial conditions
    if "state.params" in s and body and "state.params" not in body:
        draw_half = s.split("draw(", 1)[-1]
        if "state.params" not in draw_half:
            errors.append(
                "Slider values (state.params) are read neither in step() nor in draw() — "
                "moving a control would not change the running animation."
            )
    return UIVerdict(ok=(len(errors) == 0), errors=errors)


def strip_fences_only(text: str) -> str:
    """For freeform HTML that occasionally arrives fenced (handled by normalize_html
    too; kept here for symmetry)."""
    return re.sub(r"^```(?:html)?\s*|\s*```$", "", (text or "").strip())
