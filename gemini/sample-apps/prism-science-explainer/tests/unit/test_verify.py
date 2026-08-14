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
"""Unit tests for the self-heal guardrails: normalize_html (edge E1) and
static_check (edges E2/E9 — truncation, unbalanced scripts, oversize)."""

from app import config
from app.verify import normalize_html, static_check

VALID = (
    '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>T</title>'
    "</head><body><h1>Gradient Descent</h1><p>An interactive explainer with enough "
    "content to clear the minimum length threshold for a real page.</p>"
    '<canvas id="c"></canvas><script>const s={};function render(){}render();</script>'
    "</body></html>"
)


def test_valid_html_passes():
    v = static_check(VALID)
    assert v.ok, v.errors


def test_truncated_html_fails():
    # Missing closing </html> (edge E9: token-truncated generation).
    v = static_check(VALID.replace("</html>", ""))
    assert not v.ok
    assert any("</html>" in e for e in v.errors)


def test_unbalanced_script_fails():
    # One <script> with no closing tag (edge E2).
    broken = VALID.replace("</script>", "")
    v = static_check(broken)
    assert not v.ok
    assert any("script" in e.lower() for e in v.errors)


def test_missing_root_fails():
    v = static_check("<div>just a fragment, no doctype or html root at all</div>" * 5)
    assert not v.ok


def test_too_short_fails():
    v = static_check("<html></html>")
    assert not v.ok


def test_oversize_fails():
    big = VALID.replace(
        "</body>", "<p>" + ("x" * (config.HTML_MAX_CHARS + 10)) + "</p></body>"
    )
    v = static_check(big)
    assert not v.ok
    assert any("cap" in e.lower() or "exceeds" in e.lower() for e in v.errors)


def test_normalize_strips_markdown_fence():
    # Edge E1: model wraps output in a ```html fence.
    fenced = "```html\n" + VALID + "\n```"
    out = normalize_html(fenced)
    assert out.lower().startswith("<!doctype html")
    assert "```" not in out
    assert static_check(out).ok


def test_normalize_strips_leading_prose():
    prose = "Sure! Here is your interactive explainer:\n\n" + VALID
    out = normalize_html(prose)
    assert out.lower().startswith("<!doctype html")
    assert "Sure!" not in out


def test_normalize_empty_is_safe():
    assert normalize_html("") == ""
    assert normalize_html(None) == ""  # type: ignore[arg-type]


def test_normalize_clean_html_unchanged():
    assert normalize_html(VALID) == VALID.strip()
