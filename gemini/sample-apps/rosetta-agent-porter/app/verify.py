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
"""Layered static verification of a generated ADK project (cheap -> thorough).

  1. ast.parse each app/*.py         — syntax, in-process, no deps needed
  2. agents-cli lint --fix           — ruff/ty/codespell (needs project deps)
  3. uv run python -c import app.agent — the ADK-wiring gate (needs project deps)

Feeds the self-heal loop: any errors here become the fixer's `verdict_errors`.
"""

from __future__ import annotations

import ast
from pathlib import Path

from app import acli
from app.schemas import PortVerdict


def _py_files(project: Path) -> list[Path]:
    app = project / "app"
    return sorted(app.rglob("*.py")) if app.exists() else []


def check_syntax(project: Path) -> list[str]:
    errs: list[str] = []
    for p in _py_files(project):
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError as e:
            rel = p.relative_to(project)
            errs.append(f"{rel}:{e.lineno}: SyntaxError: {e.msg}")
    return errs


def _tail(text: str, n: int = 40) -> str:
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


def static_check(
    project: Path,
    *,
    do_lint: bool = True,
    do_import: bool = True,
    do_runtime: bool = True,
    runtime_prompt: str = "hello",
) -> PortVerdict:
    """Run the layered checks cheap->thorough, short-circuiting so we never lint /
    import / run code that failed an earlier (cheaper) gate:

      syntax (ast) -> lint (ruff/ty) -> import (ADK wiring) -> runtime (turn-1 run).

    The runtime layer actually executes the ported agent on a trivial input, which
    catches Event.content type errors and callback-signature bugs that pass import
    but crash at run time. Any error becomes a fixer `verdict_errors` entry.
    """
    errs = check_syntax(project)
    if errs:
        return PortVerdict(ok=False, errors=errs)

    if do_lint:
        r = acli.lint(project, fix=True)
        if not r.ok:
            errs.append("agents-cli lint failed:\n" + _tail(r.text, 40))

    if do_import:
        r = acli.import_smoke(project)
        if not r.ok:
            errs.append("`import app.agent` failed:\n" + _tail(r.err or r.out, 40))

    # Only run the (slow, real-model) runtime smoke once the code parses, lints and
    # imports — otherwise we'd waste a run on code we already know is broken.
    if do_runtime and not errs:
        r = acli.runtime_smoke(project, prompt=runtime_prompt)
        if not r.ok or "RUNTIME_FAIL" in r.text:
            errs.append(
                "runtime smoke (agent crashed on turn 1):\n" + _tail(r.text, 45)
            )

    return PortVerdict(ok=(len(errs) == 0), errors=errs)
