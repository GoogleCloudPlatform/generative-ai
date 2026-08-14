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
"""Deterministic repo I/O for Rosetta (no LLM here).

Clone/copy a source repo into the scratch workspace, build a compact manifest the
`intake` agent can read to detect the framework + pick files, then assemble the
bounded per-facet source/doc blocks the analysis swarm reads.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from app import config

# Scratch workspace for cloned source repos + generated ADK projects. Overridable
# via ROSETTA_WORKSPACE so a container deploy can point it at a writable volume
# (e.g. /tmp/rosetta-workspace on Cloud Run); defaults to ./workspace locally.
WORKSPACE = Path(
    os.environ.get("ROSETTA_WORKSPACE")
    or (Path(__file__).resolve().parent.parent / "workspace")
)
SOURCE_DIR = WORKSPACE / "source"
PORTED_DIR = WORKSPACE / "ported"

# Directories we never descend into.
_SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "site-packages",
    ".next",
    ".turbo",
    "target",
}
_CODE_EXT = {".py"}
_DOC_EXT = {".md", ".mdx", ".rst", ".txt", ".ipynb"}
_CFG_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "langgraph.json",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "poetry.lock",
}
_SECRET_HINT = re.compile(r"(?:_KEY|_SECRET|_TOKEN|PASSWORD|API_KEY)\s*=", re.I)


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (s or "agent")[:26]


# Code hosts where we understand the owner/repo[/subdir] URL shape, so users can
# paste a browser URL that points *into* a monorepo (…/tree/<ref>/<subdir>) or a
# scheme-less shorthand (github.com/owner/repo).
_KNOWN_HOSTS = ("github.com", "gitlab.com", "bitbucket.org")


def _basename(s: str) -> str:
    base = s.rstrip("/").split("/")[-1]
    base = base[:-4] if base.endswith(".git") else base
    return base or "agent"


def _parse_source(url_or_path: str) -> dict:
    """Classify a Rosetta source string into how we should fetch it.

    Returns either:
      {"kind":"git",  "clone_url":str, "subdir":str|None, "ref":str|None, "name":str}
      {"kind":"local","path":str, "name":str}

    Beyond full git URLs it understands, so the UI chips and pasted browser URLs
    both work:
      github.com/o/r                       -> https://github.com/o/r
      github.com/o/r/sub/dir               -> clone o/r, descend into sub/dir
      https://github.com/o/r/tree/<ref>/x  -> clone o/r @<ref>, descend into x
      www. prefixes, trailing slashes, and .git suffixes are tolerated.
    Anything that isn't an HTTP(S)/git URL is treated as a local filesystem path
    (preserves the local-copy path used by the CLI harness and tests).
    """
    s = (url_or_path or "").strip()

    # 1) Explicit non-HTTP git transports: clone verbatim, no subdir parsing.
    if s.startswith(("git@", "ssh://", "git://")):
        return {
            "kind": "git",
            "clone_url": s,
            "subdir": None,
            "ref": None,
            "name": _basename(s),
        }

    # 2) Strip an HTTP(S) scheme (if any) so scheme-ful and scheme-less host URLs
    #    take the same parsing path.
    had_http = bool(re.match(r"^https?://", s, re.I))
    body = re.sub(r"^https?://", "", s, flags=re.I)
    body = re.sub(r"^www\.", "", body, flags=re.I)
    parts = [p for p in body.split("/") if p]

    # 3) Known code hosts: parse owner/repo[/tree|blob/<ref>][/subdir...].
    if len(parts) >= 3 and parts[0].lower() in _KNOWN_HOSTS:
        host = parts[0].lower()
        owner = parts[1]
        repo = parts[2][:-4] if parts[2].endswith(".git") else parts[2]
        rest = parts[3:]
        ref = None
        if rest and rest[0] in ("tree", "blob") and len(rest) >= 2:
            ref = rest[1]
            rest = rest[2:]
        subdir = "/".join(rest) or None
        return {
            "kind": "git",
            "clone_url": f"https://{host}/{owner}/{repo}",
            "subdir": subdir,
            "ref": ref,
            "name": _basename(subdir) if subdir else repo,
        }

    # 4) Generic remote with an explicit http(s) scheme (unknown host): clone as-is.
    if had_http:
        return {
            "kind": "git",
            "clone_url": s,
            "subdir": None,
            "ref": None,
            "name": _basename(s),
        }

    # 5) Otherwise: a local filesystem path.
    return {"kind": "local", "path": s, "name": _basename(s)}


def repo_name(url_or_path: str) -> str:
    """Effective workspace dir name for a source (subdir leaf, or repo name)."""
    return _parse_source(url_or_path)["name"]


def _git(args: list[str], timeout: int = 300) -> None:
    r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip().splitlines()
        raise RuntimeError(
            f"git {args[0]}: {tail[-1] if tail else 'exit ' + str(r.returncode)}"
        )


def clone_repo(url_or_path: str, dest: Path | None = None) -> Path:
    """Fetch a source repo into the workspace and return its local directory.

    Handles full/scheme-less git URLs, monorepo subdirectories (fetched with a
    sparse, tree-filtered clone so we don't download the whole monorepo), and
    local paths. Raises with a clear message on failure.
    """
    info = _parse_source(url_or_path)
    dest = dest or (SOURCE_DIR / info["name"])
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Local path: copy a snapshot in.
    if info["kind"] == "local":
        src = Path(info["path"]).expanduser().resolve()
        if not src.exists():
            raise FileNotFoundError(f"local path not found: {src}")
        shutil.copytree(
            src, dest, ignore=shutil.ignore_patterns(*_SKIP_DIRS), dirs_exist_ok=True
        )
        return dest

    branch = ["--branch", info["ref"]] if info["ref"] else []
    tmp = dest.parent / f"{info['name']}.__clone__"
    if tmp.exists():
        shutil.rmtree(tmp)

    try:
        if info["subdir"]:
            # Sparse, tree-filtered clone: pull only the target subtree, not the
            # entire (possibly huge) monorepo. Fall back to a plain shallow clone
            # if the server/git can't do partial+sparse.
            try:
                _git(
                    [
                        "clone",
                        "--depth",
                        "1",
                        "--filter=tree:0",
                        "--sparse",
                        *branch,
                        info["clone_url"],
                        str(tmp),
                    ]
                )
                _git(["-C", str(tmp), "sparse-checkout", "set", info["subdir"]])
            except RuntimeError:
                shutil.rmtree(tmp, ignore_errors=True)
                _git(["clone", "--depth", "1", *branch, info["clone_url"], str(tmp)])
            picked = tmp / info["subdir"]
            if not picked.is_dir():
                raise FileNotFoundError(
                    f"subdirectory '{info['subdir']}' not found in {info['clone_url']}"
                )
            shutil.move(str(picked), str(dest))
        else:
            _git(["clone", "--depth", "1", *branch, info["clone_url"], str(tmp)])
            shutil.move(str(tmp), str(dest))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Drop any .git dir; we only need a snapshot.
    shutil.rmtree(dest / ".git", ignore_errors=True)
    return dest


def _iter_files(repo_dir: Path):
    for p in sorted(repo_dir.rglob("*")):
        if p.is_dir():
            continue
        if any(part in _SKIP_DIRS for part in p.relative_to(repo_dir).parts):
            continue
        yield p


def _read_text(p: Path, cap: int) -> str:
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if len(t) > cap:
        t = t[:cap] + f"\n... [truncated {len(t) - cap} chars]"
    return t


def build_manifest(repo_dir: Path) -> dict:
    """Compact structural summary + code previews for the intake agent."""
    files: list[dict] = []
    tree_lines: list[str] = []
    total_loc = 0
    for p in _iter_files(repo_dir):
        rel = str(p.relative_to(repo_dir))
        ext = p.suffix.lower()
        kind = (
            "code"
            if ext in _CODE_EXT
            else "doc"
            if ext in _DOC_EXT
            else "config"
            if p.name in _CFG_NAMES
            else "other"
        )
        size = p.stat().st_size
        if kind in ("code", "doc", "config"):
            loc = 0
            if kind == "code":
                loc = _read_text(p, 4_000_000).count("\n") + 1
                total_loc += loc
            files.append({"path": rel, "kind": kind, "size": size, "loc": loc})
        if len(tree_lines) < 250:
            tree_lines.append(rel)
    return {
        "root": repo_dir.name,
        "tree": "\n".join(tree_lines),
        "files": files,
        "total_loc": total_loc,
        "n_code": sum(1 for f in files if f["kind"] == "code"),
    }


def manifest_block(repo_dir: Path, manifest: dict, *, max_chars: int = 40_000) -> str:
    """Text the intake agent reads: tree + config files + head-previews of code."""
    out = [
        f"REPO: {manifest['root']}",
        f"~{manifest['total_loc']} LOC · {manifest['n_code']} python files",
        "",
        "FILE TREE:",
        manifest["tree"],
        "",
    ]
    # config files (small, full)
    for f in manifest["files"]:
        if f["kind"] == "config":
            body = _read_text(repo_dir / f["path"], 3000)
            out.append(f"=== {f['path']} ===\n{body}\n")
    # code previews (head), largest/most-central first
    code = sorted(
        (f for f in manifest["files"] if f["kind"] == "code"),
        key=lambda f: (-("src/" in f["path"]), -f["loc"]),
    )
    used = sum(len(x) for x in out)
    for f in code[:30]:
        head = "\n".join(_read_text(repo_dir / f["path"], 6000).splitlines()[:45])
        block = f"=== {f['path']}  (~{f['loc']} LOC, HEAD) ===\n{head}\n"
        if used + len(block) > max_chars:
            break
        out.append(block)
        used += len(block)
    return "\n".join(out)


def _pick(paths: list[str], repo_dir: Path, predicate) -> list[str]:
    return [p for p in paths if predicate(p) and (repo_dir / p).exists()]


def build_source_blocks(
    repo_dir: Path, files_to_analyze: list[str], manifest: dict
) -> dict[str, str]:
    """Assemble the bounded blocks the swarm reads:

    source_block : concatenated code files_to_analyze (with path headers)
    docs_block   : README + tests + notebooks + docstring-bearing examples
    """
    # code block
    code_files = (
        files_to_analyze
        or [
            f["path"]
            for f in sorted(manifest["files"], key=lambda f: -f["loc"])
            if f["kind"] == "code"
        ][: config.MAX_SOURCE_FILES]
    )
    code_files = [p for p in code_files if (repo_dir / p).exists()][
        : config.MAX_SOURCE_FILES
    ]

    parts: list[str] = []
    used = 0
    for rel in code_files:
        body = _read_text(repo_dir / rel, config.MAX_FILE_CHARS)
        block = f"\n===== FILE: {rel} =====\n{body}\n"
        if used + len(block) > config.MAX_SOURCE_BLOCK_CHARS:
            break
        parts.append(block)
        used += len(block)
    source_block = "".join(parts) or "(no source files found)"

    # docs block: README, tests, notebooks, example scripts
    all_paths = [f["path"] for f in manifest["files"]]
    doc_candidates = (
        _pick(all_paths, repo_dir, lambda p: p.lower().endswith("readme.md"))
        + _pick(
            all_paths,
            repo_dir,
            lambda p: "/test" in p.lower() or p.lower().startswith("test"),
        )
        + _pick(all_paths, repo_dir, lambda p: p.lower().endswith(".ipynb"))
        + _pick(
            all_paths, repo_dir, lambda p: "example" in p.lower() and p.endswith(".py")
        )
    )
    doc_parts: list[str] = []
    doc_used = 0
    seen: set[str] = set()
    for rel in doc_candidates:
        if rel in seen:
            continue
        seen.add(rel)
        body = _read_text(repo_dir / rel, 8000)
        block = f"\n===== {rel} =====\n{body}\n"
        if doc_used + len(block) > config.MAX_SOURCE_BLOCK_CHARS:
            break
        doc_parts.append(block)
        doc_used += len(block)
    docs_block = "".join(doc_parts) or "(no README/tests/examples found)"

    return {"source_block": source_block, "docs_block": docs_block}


def secret_scan(repo_dir: Path) -> list[str]:
    """Cheap heuristic: flag files that look like they contain inline secrets."""
    hits: list[str] = []
    for p in _iter_files(repo_dir):
        if p.suffix.lower() in {".py", ".env", ".cfg", ".toml", ".yaml", ".yml"}:
            t = _read_text(p, 200_000)
            for m in _SECRET_HINT.finditer(t):
                seg = t[m.start() : m.start() + 60]
                if re.search(r"=\s*[\"'][A-Za-z0-9_\-]{16,}", seg):
                    hits.append(str(p.relative_to(repo_dir)))
                    break
    return hits
