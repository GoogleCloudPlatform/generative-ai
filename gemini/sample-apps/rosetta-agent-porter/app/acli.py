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
"""Thin subprocess wrappers around `agents-cli` / `adk` / `uv`.

This is mechanism (c) of the skill-integration design: the Python orchestrator
literally drives the toolchain the agents-cli skills describe — scaffold the
ported project, install its deps, lint it, run it, eval it, and launch its
api_server for the live chat.
"""

from __future__ import annotations

import contextlib
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Run:
    ok: bool
    code: int
    out: str
    err: str

    @property
    def text(self) -> str:
        return (self.out + "\n" + self.err).strip()


# Console scripts we shell out to that are installed as Python dependencies.
# `uv` is deliberately NOT here: it is a standalone tool, not a project dep.
_VENV_SCRIPTS = ("agents-cli", "adk")


def _resolve(program: str) -> str:
    """Prefer the console script next to the running interpreter, else PATH.

    `uv run python serve.py` puts .venv/bin on PATH, but `python serve.py` and
    `.venv/bin/python serve.py` do not. Without this, those launches silently
    pick up a DIFFERENT agents-cli from the user's PATH — or none at all, which
    surfaces as a confusing scaffold failure rather than "tool not installed".
    """
    if program in _VENV_SCRIPTS:
        candidate = Path(sys.executable).parent / program
        if candidate.exists():
            return str(candidate)
    return program


def _run(
    cmd: list[str], cwd: Path | None = None, timeout: int = 600, env: dict | None = None
) -> Run:
    cmd = [_resolve(cmd[0]), *cmd[1:]]
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return Run(p.returncode == 0, p.returncode, p.stdout or "", p.stderr or "")
    except subprocess.TimeoutExpired as e:
        return Run(False, 124, e.stdout or "", f"timeout after {timeout}s")
    except FileNotFoundError as e:
        return Run(False, 127, "", str(e))


# --------------------------------------------------------------------------- #
# scaffold / install / lint
# --------------------------------------------------------------------------- #
def scaffold_create(name: str, out_dir: Path, *, agent_dir: str = "app") -> Run:
    """`agents-cli scaffold create <name> --agent adk --prototype -y -o <out_dir>`.

    The CLI creates <out_dir>/<name> itself — do NOT pre-create it.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    return _run(
        [
            "agents-cli",
            "scaffold",
            "create",
            name,
            "--agent",
            "adk",
            "--prototype",
            "--deployment-target",
            "none",
            "--agent-directory",
            agent_dir,
            "--output-dir",
            str(out_dir),
            "--yes",
            "--skip-checks",
        ],
        timeout=300,
    )


def install(project: Path) -> Run:
    return _run(["agents-cli", "install"], cwd=project, timeout=600)


def uv_sync(project: Path) -> Run:
    return _run(["uv", "sync"], cwd=project, timeout=600)


def uv_add(project: Path, requirements: list[str]) -> Run:
    """Add third-party runtime deps to the ported project (`uv add pkg ...`).

    Needed when the SOURCE agent leans on a domain library for CORRECTNESS
    (python-chess for legal moves, a parser, a solver...). The generator may only
    write files under app/, so without this it reimplements such a library from
    scratch and gets it subtly wrong — see build.apply_extra_deps.
    """
    return _run(["uv", "add", *requirements], cwd=project, timeout=600)


def lint(project: Path, fix: bool = True) -> Run:
    cmd = ["agents-cli", "lint"]
    if fix:
        cmd.append("--fix")
    return _run(cmd, cwd=project, timeout=300)


# --------------------------------------------------------------------------- #
# run / eval
# --------------------------------------------------------------------------- #
def run_prompt(
    project: Path, prompt: str, verbose: bool = False, timeout: int = 300
) -> Run:
    cmd = ["agents-cli", "run", prompt]
    if verbose:
        cmd.append("-v")
    return _run(cmd, cwd=project, timeout=timeout)


def eval_generate(project: Path, timeout: int = 900) -> Run:
    return _run(["agents-cli", "eval", "generate"], cwd=project, timeout=timeout)


def eval_grade(project: Path, timeout: int = 900) -> Run:
    return _run(["agents-cli", "eval", "grade"], cwd=project, timeout=timeout)


# --------------------------------------------------------------------------- #
# import smoke (the ADK-wiring gate) — runs in the ported project's own env
# --------------------------------------------------------------------------- #
def import_smoke(project: Path, module: str = "app.agent", timeout: int = 120) -> Run:
    return _run(
        ["uv", "run", "python", "-c", f"import {module}"], cwd=project, timeout=timeout
    )


_RUNTIME_DRIVER = """\
import asyncio, sys, traceback
INNER = float(sys.argv[2]) if len(sys.argv) > 2 else 40.0

async def go():
    from app.agent import root_agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    runner = InMemoryRunner(agent=root_agent, app_name="app")
    await runner.session_service.create_session(app_name="app", user_id="u", session_id="s")
    msg = types.Content(role="user", parts=[types.Part(text=sys.argv[1])])
    async for _ in runner.run_async(user_id="u", session_id="s", new_message=msg):
        pass

try:
    asyncio.run(asyncio.wait_for(go(), timeout=INNER))
    print("RUNTIME_OK")
except (asyncio.TimeoutError, TimeoutError):
    print("RUNTIME_OK")  # started cleanly, just long-running — turn-1 crashes fire fast
except BaseException:
    traceback.print_exc()
    print("RUNTIME_FAIL")
    sys.exit(1)
"""


def runtime_smoke(
    project: Path,
    prompt: str = "hello",
    inner_timeout: float = 40.0,
    timeout: int = 150,
) -> Run:
    """Actually RUN the ported root_agent on a trivial input in its own venv, to
    catch turn-1 runtime crashes (Event.content type errors, callback signature
    bugs) that import/lint miss. Completion OR a clean timeout = OK; an exception
    = fail (traceback returned for the fixer)."""
    driver = project / "_rosetta_smoke.py"
    driver.write_text(_RUNTIME_DRIVER, encoding="utf-8")
    try:
        r = _run(
            ["uv", "run", "python", "_rosetta_smoke.py", prompt, str(inner_timeout)],
            cwd=project,
            timeout=timeout,
        )
        if r.code == 124:  # outer timeout: it ran without an early crash -> OK
            return Run(True, 0, "RUNTIME_OK (outer timeout)", "")
        return r
    finally:
        driver.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# run_capture — RUN the ported root_agent and capture its final answer text.
# Used by the fidelity-eval engine (app/evalgen.py): drive the port on a real
# mined input inside its OWN venv, harvest the model's final response so an
# LLM judge can grade behavioral faithfulness against the original agent.
# --------------------------------------------------------------------------- #
_CAPTURE_BEGIN = "===CAPTURE_BEGIN==="
_CAPTURE_END = "===CAPTURE_END==="
_CAPTURE_ERROR = "===CAPTURE_ERROR==="

# Runs in the ported project's env. Iterates the agent's events, collects the
# final model response text (non-thought text parts of the last content turn),
# and prints it between unique markers. On inner timeout it still emits whatever
# was collected so far; on any exception it prints the traceback under an error
# marker and exits non-zero.
_CAPTURE_DRIVER = f'''\
import asyncio, sys, traceback

PROMPT = sys.argv[1] if len(sys.argv) > 1 else "hello"
INNER = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0

_final = []      # finalized final-response texts (one entry per content turn)
_partial = []    # streaming partial buffer for the in-flight turn (if any)


def _emit():
    text = _final[-1] if _final else "".join(_partial)
    print("{_CAPTURE_BEGIN}")
    print(text)
    print("{_CAPTURE_END}")


async def go():
    from app.agent import root_agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=root_agent, app_name="app")
    await runner.session_service.create_session(
        app_name="app", user_id="u", session_id="s"
    )
    msg = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    async for event in runner.run_async(user_id="u", session_id="s", new_message=msg):
        content = getattr(event, "content", None)
        if content is None:
            continue
        if getattr(content, "role", None) == "user":
            continue  # tool/function responses come back as role 'user'
        texts = []
        for part in getattr(content, "parts", None) or []:
            t = getattr(part, "text", None)
            if not t or getattr(part, "thought", False):
                continue  # ignore empty + thought-signature parts
            texts.append(t)
        if not texts:
            continue  # tool-call / function-response turns carry no answer text
        joined = "".join(texts)
        if getattr(event, "partial", False):
            _partial.append(joined)
        else:
            _final.append(joined)
            _partial.clear()


try:
    try:
        asyncio.run(asyncio.wait_for(go(), timeout=INNER))
    except (asyncio.TimeoutError, TimeoutError):
        pass  # long-running: emit whatever text we collected before the timeout
    _emit()
except BaseException:
    print("{_CAPTURE_ERROR}")
    traceback.print_exc()
    sys.exit(1)
'''


def run_capture(
    project: Path,
    prompt: str,
    inner_timeout: float = 120.0,
    timeout: int = 180,
) -> tuple[bool, str]:
    """Run the ported root_agent on `prompt` in its OWN venv and capture the final
    model response text.

    Mirrors `runtime_smoke`: writes a temp `_rosetta_capture.py` driver into the
    project, runs it via `uv run`, then deletes it. Returns `(ok, text)` where
    `ok` is True iff non-empty text was captured (True even on a clean inner
    timeout that still produced text); False on error/empty. `text` is the
    captured answer on success, or a short error/traceback tail on failure.
    """
    driver = project / "_rosetta_capture.py"
    driver.write_text(_CAPTURE_DRIVER, encoding="utf-8")
    try:
        r = _run(
            ["uv", "run", "python", "_rosetta_capture.py", prompt, str(inner_timeout)],
            cwd=project,
            timeout=timeout,
        )
    finally:
        driver.unlink(missing_ok=True)

    out = r.out or ""
    if _CAPTURE_BEGIN in out and _CAPTURE_END in out:
        body = out.split(_CAPTURE_BEGIN, 1)[1].split(_CAPTURE_END, 1)[0]
        text = body.strip("\n").strip()
        return (bool(text), text)

    # No markers: driver crashed, errored, or the outer timeout (124) killed it
    # before it could emit. Surface a tail for the caller/judge to record.
    tail = (r.err or out or f"no output (exit {r.code})").strip()
    return (False, tail[-2000:])


# --------------------------------------------------------------------------- #
# api_server (the live chat backend) — long-running; caller manages the handle
# --------------------------------------------------------------------------- #
def start_api_server(project: Path, port: int, log_path: Path) -> subprocess.Popen:
    """Launch `adk api_server` for the ported project on `port`. Returns the Popen.

    adk api_server serves POST /run and POST /run_sse over the agents in the dir.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(
        log_path, "w"
    )  # handle outlives this scope: (handle lives with the process
    return subprocess.Popen(
        [
            "uv",
            "run",
            "adk",
            "api_server",
            ".",
            "--port",
            str(port),
            "--host",
            "127.0.0.1",
        ],
        cwd=str(project),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        # Own process group. `uv run` execs a GRANDCHILD (the real uvicorn), and
        # terminating only the uv wrapper leaves that grandchild alive holding the
        # port — the next port then dies with "address already in use" and the
        # cockpit reports "ported api_server failed to boot". stop_api_server()
        # signals the whole group.
        start_new_session=True,
    )


def stop_api_server(proc: subprocess.Popen | None, timeout: float = 10.0) -> None:
    """Stop an api_server started above, including its uvicorn grandchild."""
    if proc is None or proc.poll() is not None:
        return
    try:
        pgid = os.getpgid(proc.pid)
    except (ProcessLookupError, PermissionError):
        pgid = None

    if pgid is None:
        proc.terminate()
    else:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(pgid, signal.SIGTERM)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if pgid is not None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(pgid, signal.SIGKILL)
        else:
            proc.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)


def wait_port_free(port: int, host: str = "127.0.0.1", timeout: float = 15.0) -> bool:
    """Block until nothing is listening on `port`. Returns False on timeout.

    Process exit and socket release are not the same instant, so the relaunch has
    to wait for the socket, not just the pid.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) != 0:  # nothing accepting -> free
                return True
        time.sleep(0.3)
    return False
