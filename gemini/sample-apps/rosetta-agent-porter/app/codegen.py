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
"""Parse the code generator's delimited-file output and write it to disk safely,
plus the pretty-print helpers that build the prompt injection blocks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.runtime import as_dict
from app.schemas import PortedFile

_FILE_RE = re.compile(r"^===FILE:\s*(.+?)\s*===\s*$", re.MULTILINE)
_FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n|\n?```\s*$")


def _clean(body: str) -> str:
    b = body.strip("\n")
    # Defensive: strip a wrapping ```python ... ``` if the model added one.
    if b.lstrip().startswith("```"):
        b = _FENCE.sub("", b.strip())
    return b.rstrip() + "\n"


def parse_files(raw: str) -> list[PortedFile]:
    """Parse `===FILE: path===\\n<content>` blocks (terminated by the next marker or
    `===END===`). Returns a list of PortedFile; unparseable input -> []."""
    if not raw:
        return []
    raw = raw.replace("===END===", "").strip()
    matches = list(_FILE_RE.finditer(raw))
    files: list[PortedFile] = []
    for i, m in enumerate(matches):
        path = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = _clean(raw[start:end])
        if path and body.strip():
            files.append(PortedFile(path=path, content=body))
    return files


def _safe_rel(path: str) -> str | None:
    p = path.strip().lstrip("/")
    if ".." in Path(p).parts or Path(p).is_absolute():
        return None
    return p


def write_files(project_root: Path, files: list[PortedFile]) -> list[str]:
    """Write files under project_root. Rejects path traversal. Returns written paths."""
    written: list[str] = []
    for f in files:
        rel = _safe_rel(f.path)
        if rel is None:
            continue
        dst = project_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(f.content, encoding="utf-8")
        written.append(rel)
    return written


# --------------------------------------------------------------------------- #
# prompt-injection block builders (pretty, bounded strings)
# --------------------------------------------------------------------------- #
def _j(v) -> str:
    d = as_dict(v)
    return json.dumps(d, indent=2, ensure_ascii=False) if d is not None else "(none)"


def analyses_block(state: dict) -> str:
    """Compact, readable JSON of the swarm analyses for planner/codegen."""
    parts = []
    for key, label in [
        ("analysis_graph", "GRAPH"),
        ("analysis_tools", "TOOLS"),
        ("analysis_state", "STATE / REDUCERS"),
        ("analysis_models", "MODELS / KNOBS"),
    ]:
        parts.append(f"## {label}\n{_j(state.get(key))}")
    return "\n\n".join(parts)


def prompts_block(state: dict) -> str:
    """The source prompts, verbatim, for faithful porting."""
    d = as_dict(state.get("analysis_prompts")) or {}
    out = []
    for p in d.get("prompts", []):
        out.append(
            f"--- owner={p.get('owner', '?')} name={p.get('name', '?')} ---\n{p.get('text', '')}"
        )
    return "\n\n".join(out) or "(no prompts extracted)"


def plan_block(state: dict) -> str:
    return _j(state.get("port_plan"))


def broken_block(files: list[PortedFile]) -> str:
    return "\n\n".join(f"===FILE: {f.path}===\n{f.content}" for f in files)
