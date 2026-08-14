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
"""Fast, server-side static verification of model-generated HTML (no browser).

The runtime half of the self-heal loop (window.onerror / CSP capture) lives in
the frontend; this catches the cheap failures before we ever stream to a client.
"""

import re

from app import config
from app.schemas import UIVerdict


def normalize_html(text: str) -> str:
    """Strip markdown fences / prose so the output is a raw HTML document (edge E1)."""
    if not text:
        return ""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:html)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t)
    m = re.search(r"(<!doctype html|<html)", t, flags=re.IGNORECASE)
    if m:
        t = t[m.start() :]
    return t.strip()


def static_check(html: str) -> UIVerdict:
    """Cheap structural validity check. Lenient: flag likely-broken output only."""
    errors: list[str] = []
    h = html or ""
    low = h.lower()

    if len(h) < 200:
        errors.append("Output too short to be a valid page.")
    if "<!doctype html" not in low and "<html" not in low:
        errors.append("Missing <!DOCTYPE html> / <html> root element.")
    if "</html>" not in low:
        errors.append("Missing closing </html> (output likely truncated).")
    if "<body" not in low:
        errors.append("Missing <body> element.")

    opens = len(re.findall(r"<script\b", low))
    closes = len(re.findall(r"</script>", low))
    if opens != closes:
        errors.append(f"Unbalanced <script> tags ({opens} open vs {closes} close).")

    if len(h) > config.HTML_MAX_CHARS:
        errors.append(
            f"Output exceeds size cap ({len(h)} > {config.HTML_MAX_CHARS} chars)."
        )

    return UIVerdict(ok=(len(errors) == 0), errors=errors)
