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
"""Small helpers to run a single ADK agent with a seeded session.state and read
results back. Used by tests and the orchestrator's isolated-run paths."""

from __future__ import annotations

import json
import uuid

from google.adk.agents import BaseAgent
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


async def run_agent(agent: BaseAgent, seed_state: dict, message: str = "go") -> dict:
    """Run `agent` once with `seed_state` pre-loaded into session.state; return the
    final session.state dict."""
    app = App(root_agent=agent, name="app")
    svc = InMemorySessionService()
    runner = Runner(app=app, session_service=svc)
    uid, sid = "rosetta", uuid.uuid4().hex
    await svc.create_session(
        app_name="app", user_id=uid, session_id=sid, state=dict(seed_state)
    )
    msg = types.Content(role="user", parts=[types.Part(text=message)])
    async for _ in runner.run_async(user_id=uid, session_id=sid, new_message=msg):
        pass
    sess = await svc.get_session(app_name="app", user_id=uid, session_id=sid)
    return dict(sess.state)


def as_dict(v):
    """Coerce a state value (which may be a JSON string or a model) to a dict."""
    if v is None:
        return None
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return None
    if hasattr(v, "model_dump"):
        return v.model_dump()
    return v
