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
"""Prism UI server: a lean FastAPI + SSE frontend for the Prism pipeline.

One process: this server hosts the single-page UI AND runs the ADK multi-agent
pipeline in-process via a Runner. The browser talks only to /api/prism, which
streams server-sent events as the pipeline runs.

App-level SSE events emitted to the browser:
  phase / plan / finding / citation / ui_chunk / verdict / metrics / ui_done /
  declined / error / end   (see the frontend for the payload shapes)
"""

import json
import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.events import APP_NAME, PRISM_EVENT

FRONTEND = Path(__file__).parent / "frontend"

api = FastAPI(title="Prism", description="Generative science explainers")


# --- shared: map one ADK event's (author, text, partial) to an SSE frame -------
def _translate(author: str, txt: str, partial: bool):
    if txt.startswith(PRISM_EVENT):
        d = json.loads(txt[len(PRISM_EVENT) :])
        return {"event": d["type"], "data": json.dumps(d["data"])}
    if author.startswith("ui_") and partial and txt:
        # streamed HTML (freeform) or JS payload (template) -> Code tab
        return {"event": "ui_chunk", "data": json.dumps({"text": txt})}
    if author == "prism" and txt and not txt.startswith(PRISM_EVENT):
        return {"event": "ui_done", "data": json.dumps({"html": txt})}
    return None


# --- in-process ADK Runner (built lazily on the first request) ----------------
_local: dict = {}


def _local_runner():
    if "runner" not in _local:
        from google.adk.artifacts import InMemoryArtifactService
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        from app.agent import app as adk_app

        ss = InMemorySessionService()
        _local["ss"] = ss
        _local["runner"] = Runner(
            app=adk_app,
            session_service=ss,
            artifact_service=InMemoryArtifactService(),
        )
    return _local["runner"], _local["ss"]


async def _local_stream(concept: str, mode: str):
    from google.adk.agents.run_config import RunConfig, StreamingMode
    from google.genai import types

    runner, ss = _local_runner()
    uid, sid = "web", uuid.uuid4().hex
    await ss.create_session(
        app_name=APP_NAME, user_id=uid, session_id=sid, state={"mode": mode}
    )
    msg = types.Content(role="user", parts=[types.Part(text=concept)])
    cfg = RunConfig(streaming_mode=StreamingMode.SSE)
    async for ev in runner.run_async(
        user_id=uid, session_id=sid, new_message=msg, run_config=cfg
    ):
        parts = ev.content.parts if ev.content else []
        txt = "".join((p.text or "") for p in parts) if parts else ""
        out = _translate(ev.author or "", txt, getattr(ev, "partial", False))
        if out:
            yield out


def _err_detail(exc: BaseException, _depth: int = 0) -> str:
    """Flatten an exception into one readable line, unwrapping ExceptionGroups.

    ADK runs the gatekeeper+planner and the research swarm as ParallelAgents,
    i.e. inside asyncio TaskGroups. When one branch fails, the group's own
    str() is just "unhandled errors in a TaskGroup (1 sub-exception)" — the
    real cause (a 429, a 404, a schema violation) is hidden, which makes a
    mid-demo failure impossible to triage from the event stream. Recurse.
    """
    subs = getattr(exc, "exceptions", None)
    if subs and _depth < 3:
        return " | ".join(_err_detail(s, _depth + 1) for s in subs)
    return f"{type(exc).__name__}: {exc}"


async def _event_stream(concept: str, mode: str):
    try:
        async for item in _local_stream(concept, mode):
            yield item
    except Exception as e:
        logging.exception("prism run failed")
        yield {"event": "error", "data": json.dumps({"message": _err_detail(e)})}
    yield {"event": "end", "data": "{}"}


@api.get("/api/modes")
async def modes():
    from app import config

    return {
        "default": config.DEFAULT_MODE,
        "modes": [
            {"id": k, "label": v["label"], "note": v["note"]}
            for k, v in config.MODES.items()
        ],
    }


@api.post("/api/prism")
async def prism(request: Request):
    from app import config

    body = await request.json()
    concept = (body or {}).get("concept", "").strip()
    mode = (body or {}).get("mode") or config.DEFAULT_MODE
    if mode not in config.MODES:
        mode = config.DEFAULT_MODE
    if not concept:
        return JSONResponse({"error": "empty concept"}, status_code=400)
    return EventSourceResponse(_event_stream(concept, mode))


@api.get("/api/health")
async def health():
    from app import config

    return {
        "status": "ok",
        "app": APP_NAME,
        "model": config.MODEL_NAME,
        "backend": config.BACKEND_NAME,
    }


@api.get("/")
async def index():
    idx = FRONTEND / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return JSONResponse({"status": "no frontend yet"}, status_code=404)


if __name__ == "__main__":
    import uvicorn

    # Cloud Run injects PORT; PRISM_PORT wins locally. 8040 by default to stay
    # clear of the usual 8000/8080.
    host = os.environ.get("PRISM_HOST", "127.0.0.1")
    port = int(os.environ.get("PRISM_PORT") or os.environ.get("PORT") or "8040")
    uvicorn.run(api, host=host, port=port)
