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
"""Rosetta demo server.

  GET  /                     -> the cockpit frontend
  POST /api/port {repo}      -> SSE stream of the porting run (pipeline.port_repo);
                               on a green build, launches the PORTED agent's
                               `adk api_server` and emits `chat_ready`.
  POST /api/chat {message}   -> SSE proxy to the ported agent's /run_sse (the live
                               chat backend — a real ADK api_server behind us).
  GET  /api/health

Run:  uv run python serve.py   (http://127.0.0.1:8030)
"""

from __future__ import annotations

import asyncio
import atexit
import json
import os
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

# NOTE: no load_dotenv() here on purpose. `app.config` owns environment loading:
# it reads THIS project's .env (not one inherited from a parent directory) and
# lets variables you exported in your shell win. A bare load_dotenv(override=True)
# here used to do the opposite — it searched parent directories and overrode the
# caller's environment, so a stray .env above the repo could silently switch the
# Gemini backend. Import app.config first and let it decide.
from app import acli, agents, config, evalgen, pipeline

FRONTEND = Path(__file__).parent / "frontend"
PORTED_PORT = int(os.getenv("ROSETTA_PORTED_PORT", "8060"))

api = FastAPI(title="Rosetta", description="Agents that port agents")

# Live handle to the currently-served ported agent (one at a time for the demo).
PORTED: dict = {"proc": None, "base": None, "app_name": "app", "name": None}


# --------------------------------------------------------------------------- #
# ported api_server lifecycle
# --------------------------------------------------------------------------- #
def _stop_ported() -> None:
    # Kills the whole process group: `uv run adk api_server` leaves a uvicorn
    # grandchild that would otherwise keep holding PORTED_PORT.
    acli.stop_api_server(PORTED.get("proc"))
    PORTED.update({"proc": None, "base": None, "name": None})


# The ported agent runs in its OWN process group (so we can kill it and its uv
# grandchild together), which also means it does NOT die with us. Without this,
# Ctrl-C on the cockpit leaves it holding PORTED_PORT and the next run fails with
# "ported api_server failed to boot". Runs on graceful exit, including Ctrl-C.
atexit.register(_stop_ported)


async def _launch_ported(project: Path) -> str | None:
    """Start `adk api_server` for the ported project; wait until it answers."""
    _stop_ported()
    # The previous agent's socket may outlive its process by a moment. Porting a
    # second repo in one session used to race here and fail with
    # "address already in use" -> "ported api_server failed to boot".
    if not await asyncio.to_thread(acli.wait_port_free, PORTED_PORT):
        print(f"WARNING: port {PORTED_PORT} still busy; launching anyway")
    log = project / "_api_server.log"
    proc = acli.start_api_server(project, PORTED_PORT, log)
    base = f"http://127.0.0.1:{PORTED_PORT}"
    async with httpx.AsyncClient(timeout=5) as client:
        for _ in range(60):  # ~60s to boot (first run may uv-sync)
            if proc.poll() is not None:
                return None  # died on boot
            try:
                r = await client.get(f"{base}/list-apps")
                if r.status_code == 200:
                    PORTED.update({"proc": proc, "base": base, "name": project.name})
                    return base
            except Exception:  # broad except on purpose
                pass
            await asyncio.sleep(1)
    return None


# --------------------------------------------------------------------------- #
# /api/port — stream the porting run
# --------------------------------------------------------------------------- #
async def _port_stream(url: str):
    project_path = None
    green = False
    # Capture what the fidelity eval needs as the porting events stream by.
    agent_summary = ""
    mined_inputs: list[dict] = []
    analyses: dict = {}
    async for ev in pipeline.port_repo(url):
        t, d = ev["type"], ev["data"]
        if t == "framework":
            agent_summary = d.get("summary", "") or agent_summary
        elif t == "eval_inputs":
            mined_inputs = (d.get("data") or {}).get("inputs", []) or []
        elif t == "analysis":
            analyses[d.get("facet", "")] = d.get("data")
        elif t == "done":
            project_path = d.get("project")
            green = bool(d.get("build_green"))
        yield {"event": t, "data": json.dumps(d)}

    # After a green build, launch the ported agent's api_server for the live chat.
    if green and project_path:
        yield {"event": "phase", "data": json.dumps({"phase": "launching"})}
        base = await _launch_ported(Path(project_path))
        if base:
            yield {
                "event": "chat_ready",
                "data": json.dumps(
                    {"app_name": PORTED["app_name"], "name": PORTED["name"]}
                ),
            }
            # Fidelity eval runs AFTER chat is live, so testing the port isn't
            # blocked; the scorecard fills in as each case is judged.
            yield {"event": "phase", "data": json.dumps({"phase": "evaluating"})}
            try:
                async for eval_ev in evalgen.evaluate_fidelity(
                    Path(project_path), mined_inputs, agent_summary, analyses
                ):
                    yield {
                        "event": eval_ev["type"],
                        "data": json.dumps(eval_ev["data"]),
                    }
            except (
                Exception
            ) as e:  # broad except on purpose: eval must never break the demo
                yield {
                    "event": "warning",
                    "data": json.dumps({"message": f"eval skipped: {e}"}),
                }
        else:
            yield {
                "event": "error",
                "data": json.dumps({"message": "ported api_server failed to boot"}),
            }
    yield {"event": "end", "data": "{}"}


@api.post("/api/port")
async def port(request: Request):
    body = await request.json()
    url = (body or {}).get("repo", "").strip()
    if not url:
        return JSONResponse({"error": "missing repo"}, status_code=400)
    return EventSourceResponse(_port_stream(url))


# --------------------------------------------------------------------------- #
# /api/chat — proxy to the ported agent's /run_sse (same-origin for the browser)
# --------------------------------------------------------------------------- #
async def _chat_stream(message: str, session_id: str):
    base = PORTED.get("base")
    app_name = PORTED.get("app_name", "app")
    if not base:
        yield {
            "event": "error",
            "data": json.dumps({"message": "no ported agent running"}),
        }
        return
    async with httpx.AsyncClient(timeout=None) as client:
        # ensure the session exists (idempotent create)
        try:
            await client.post(
                f"{base}/apps/{app_name}/users/web/sessions/{session_id}", json={}
            )
        except Exception:  # broad except on purpose
            pass
        payload = {
            "appName": app_name,
            "userId": "web",
            "sessionId": session_id,
            "newMessage": {"role": "user", "parts": [{"text": message}]},
            "streaming": True,
        }
        try:
            async with client.stream("POST", f"{base}/run_sse", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        yield {"event": "agent", "data": line[len("data:") :].strip()}
        except Exception as e:  # broad except on purpose
            yield {"event": "error", "data": json.dumps({"message": str(e)})}
    yield {"event": "end", "data": "{}"}


@api.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = (body or {}).get("message", "").strip()
    session_id = (body or {}).get("session_id") or uuid.uuid4().hex
    if not message:
        return JSONResponse({"error": "missing message"}, status_code=400)
    return EventSourceResponse(_chat_stream(message, session_id))


@api.get("/api/health")
async def health():
    return {
        "status": "ok",
        "ported": PORTED.get("name"),
        "chat_up": bool(PORTED.get("base")),
    }


@api.get("/api/config")
async def ui_config():
    """Display config for the cockpit.

    The UI used to hardcode model names in ~20 places, which is how it ended up
    advertising a model the pipeline no longer ran. It now reads the name from
    here, so `app/config.py` stays the single source of truth. Only the public
    DISPLAY NAME is exposed — never the raw model id.
    """
    return {
        "model_name": config.MODEL_NAME,
        # Which Gemini backend is live: "Gemini Enterprise Agent Platform" or "Gemini API (AI Studio)".
        "backend": config.BACKEND_NAME,
        # Derived from the real swarm, not a hardcoded 6, so the "xN" the UI
        # prints always matches the number of analysts actually dispatched.
        "swarm_size": len(agents.build_analysis_swarm().sub_agents),
    }


@api.get("/")
async def index():
    idx = FRONTEND / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return JSONResponse(
        {"status": "rosetta up — frontend/index.html not found"}, status_code=200
    )


if __name__ == "__main__":
    import uvicorn

    _host = os.getenv("ROSETTA_HOST", "127.0.0.1")
    _port = int(os.getenv("ROSETTA_PORT", "8030"))
    print(
        f"Rosetta cockpit → http://{_host}:{_port}  (ported agent api_server on :{PORTED_PORT})"
    )
    uvicorn.run(api, host=_host, port=_port)
