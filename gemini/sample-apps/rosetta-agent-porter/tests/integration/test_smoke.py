"""Smoke test: prove config + schemas + ADK LlmAgent(output_schema) + the real
experimental models all work end to end via a Runner. Run:

    uv run pytest tests/integration/test_smoke.py -s
"""

import uuid

import pytest
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app import config, schemas


def test_config_builds_models():
    assert config.model_id("port_planner") == config.MODEL_SMART
    assert config.model_id("graph_analyst") == config.MODEL_FAST
    m = config.make_model("intake")
    assert m is not None
    cfg = config.gen_config("port_planner")
    assert cfg.thinking_config is not None


@pytest.mark.asyncio
async def test_structured_output_end_to_end():
    """An LlmAgent with output_schema=RepoScan must return valid JSON."""
    agent = LlmAgent(
        name="intake",
        model=config.make_model("intake"),
        instruction=(
            "Classify this repo description. It is a LangGraph deep-research agent.\n"
            "Return framework=langgraph, decision=ok, confidence ~0.9."
        ),
        include_contents="none",
        output_schema=schemas.RepoScan,
        output_key="scope",
        generate_content_config=config.gen_config("intake"),
    )
    app = App(root_agent=agent, name="app")
    runner = Runner(
        app=app,
        session_service=InMemorySessionService(),
    )
    uid, sid = "t", uuid.uuid4().hex
    await runner.session_service.create_session(
        app_name="app", user_id=uid, session_id=sid
    )
    msg = types.Content(role="user", parts=[types.Part(text="analyze this repo")])
    async for _ in runner.run_async(user_id=uid, session_id=sid, new_message=msg):
        pass
    sess = await runner.session_service.get_session(
        app_name="app", user_id=uid, session_id=sid
    )
    scope = sess.state.get("scope")
    assert scope is not None, "no structured output written to state"
    parsed = (
        schemas.RepoScan.model_validate(scope) if isinstance(scope, dict) else scope
    )
    print("\nRepoScan ->", parsed)
    assert parsed.framework == "langgraph"
    assert parsed.decision == "ok"
