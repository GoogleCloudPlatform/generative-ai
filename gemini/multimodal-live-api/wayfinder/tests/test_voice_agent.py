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

"""Voice agent: browser bridge, agent/tool wiring, run config, /ws routing."""

import asyncio
import json

from backend import server, voice_agent
from backend.rag import build_coordinator_for_tenant
from fastapi.testclient import TestClient
from google.genai import types

ELEMENTS = [
    {"tag": "input", "selector": "#server-name", "label": "Server name", "value": ""},
    {
        "tag": "select",
        "selector": "#region",
        "label": "Region",
        "options": [
            {"value": "us-east", "text": "US East", "selected": True},
            {"value": "us-west", "text": "US West"},
        ],
    },
]


def _bridge_with_browser(reply):
    """Bridge whose 'browser' answers every tool_call via `reply(call)`."""
    sent = []
    holder = {}

    async def send(msg):
        sent.append(msg)
        if msg["type"] == "tool_call":
            call = msg["calls"][0]
            result, elements = reply(call)
            asyncio.get_running_loop().call_soon(
                holder["bridge"].resolve, call["id"], result, elements
            )

    bridge = voice_agent.BrowserBridge(send, ELEMENTS, timeout=1.0)
    holder["bridge"] = bridge
    return bridge, sent


def test_bridge_returns_real_outcome_and_page_changes():
    after = [dict(ELEMENTS[0], value="web-prod"), ELEMENTS[1]]
    bridge, sent = _bridge_with_browser(
        lambda c: ({"success": True, "value": "web-prod"}, after)
    )
    out = asyncio.run(
        bridge.call("type_text", {"selector": "#server-name", "text": "web-prod"})
    )
    assert out["success"] is True and out["value"] == "web-prod"
    assert len(out["page_changes"]) == 1 and "#server-name" in out["page_changes"][0]
    assert sent[0]["calls"][0]["name"] == "type_text"


def test_bridge_surfaces_failures_for_self_correction():
    bridge, _ = _bridge_with_browser(
        lambda c: (
            {
                "success": False,
                "error": "Option 'eu-north' not available.",
                "options": ["us-east", "us-west"],
                "unexpected": "x" * 999,
            },
            None,
        )
    )
    out = asyncio.run(
        bridge.call("select_option", {"selector": "#region", "value": "eu-north"})
    )
    assert out["success"] is False
    assert "not available" in out["error"]
    assert out["options"] == ["us-east", "us-west"]
    assert "unexpected" not in out  # untrusted browser fields are dropped


def test_bridge_dedupes_within_a_turn_and_resets():
    calls = []
    bridge, _ = _bridge_with_browser(
        lambda c: calls.append(c) or ({"success": True}, None)
    )

    async def run():
        a = await bridge.call("click_element", {"selector": "#allow-http"})
        b = await bridge.call("click_element", {"selector": "#allow-http"})
        bridge.new_turn()
        c = await bridge.call("click_element", {"selector": "#allow-http"})
        return a, b, c

    a, b, c = asyncio.run(run())
    assert len(calls) == 2
    assert "Already done" in b["note"]


def test_bridge_times_out_gracefully():
    async def send(msg):
        pass  # browser never answers

    bridge = voice_agent.BrowserBridge(send, ELEMENTS, timeout=0.05)
    out = asyncio.run(bridge.call("click_element", {"selector": "#x"}))
    assert out["success"] is False and "in time" in out["error"]


def test_voice_agent_tools_and_async_search():
    coord = build_coordinator_for_tenant(
        website_engine_path="projects/1/locations/global/collections/c/engines/e"
    )
    bridge = voice_agent.BrowserBridge(lambda m: None, ELEMENTS)
    # Default model is GA Gemini 3.8 Live: WHEN_IDLE search, blocking UI tools, no thinking config.
    agent = voice_agent.build_voice_agent(
        coord, bridge, grounded=True, async_search=True
    )
    names = [t.name for t in agent.tools]
    assert names == [
        "search_knowledge_base",
        "click_element",
        "type_text",
        "select_option",
        "highlight_element",
        "scroll_to_element",
    ]
    assert agent.model == "gemini-3.8-live"
    assert agent.tools[0].behavior == types.Behavior.NON_BLOCKING
    assert (
        agent.tools[0].response_scheduling == types.FunctionResponseScheduling.WHEN_IDLE
    )
    assert agent.tools[1].behavior is None
    assert getattr(agent.generate_content_config, "thinking_config", None) is None
    assert "#server-name" in agent.instruction(None)

    # Opt-in Extended Thinking: async-only tools, no scheduling, thinking config.
    thinking = voice_agent.build_voice_agent(
        coord,
        bridge,
        grounded=True,
        model="gemini-3.8-live-extended-thinking",
        async_search=True,
    )
    assert all(t.behavior == types.Behavior.NON_BLOCKING for t in thinking.tools)
    assert thinking.tools[0].response_scheduling is None
    assert thinking.generate_content_config.thinking_config is not None

    vision_only = voice_agent.build_voice_agent(coord, bridge, grounded=False)
    assert "search_knowledge_base" not in [t.name for t in vision_only.tools]


def test_run_config_live_features():
    # Extended Thinking keeps proactive audio permanently on (not sent in config)
    thinking_cfg = voice_agent.build_run_config("gemini-3.8-live-extended-thinking")
    assert thinking_cfg.context_window_compression.sliding_window is not None
    assert thinking_cfg.proactivity is None
    assert thinking_cfg.session_resumption is not None
    assert (
        thinking_cfg.input_audio_transcription
        and thinking_cfg.output_audio_transcription
    )

    std_cfg = voice_agent.build_run_config("gemini-3.8-live")
    assert std_cfg.proactivity.proactive_audio is True
    assert (
        voice_agent.build_run_config(
            "gemini-3.8-live", optional_features=False
        ).proactivity
        is None
    )


def test_event_to_messages():
    from google.adk.events import Event

    ev = Event(author="wayfinder_voice", interrupted=True)
    assert voice_agent.event_to_messages(ev) == [{"type": "interrupted"}]
    ev = Event(
        author="wayfinder_voice",
        turn_complete=True,
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    inline_data=types.Blob(data=b"\x01\x02", mime_type="audio/pcm")
                )
            ],
        ),
    )
    msgs = voice_agent.event_to_messages(ev)
    assert msgs[0]["type"] == "audio" and msgs[-1] == {"type": "turn_complete"}


class FakeVoice:
    instances = []

    def __init__(self, **kw):
        self.kw, self.calls = kw, []
        self.user_id, self.session_id = kw["user_id"], "s1"
        FakeVoice.instances.append(self)

    async def run(self):
        await asyncio.sleep(3600)

    def send_audio(self, data, mime):
        self.calls.append(("audio", data, mime))

    def send_image(self, data):
        self.calls.append(("image", data))

    def send_text(self, text):
        self.calls.append(("text", text))

    def tool_result(self, call_id, result, elements):
        self.calls.append(("tool_result", call_id, result, len(elements)))

    def update_elements(self, elements):
        self.calls.append(("elements", len(elements)))

    def close(self):
        self.calls.append(("close",))


def test_ws_routes_to_adk_engine(monkeypatch):
    monkeypatch.setattr(server, "VoiceSession", FakeVoice)
    FakeVoice.instances.clear()
    client = TestClient(server.app)
    with client.websocket_connect(
        "/ws", headers={"Origin": "http://localhost:8080"}
    ) as ws:
        ws.send_text(json.dumps({"type": "init", "url": "http://localhost:8080/cloud"}))
        ws.send_text(json.dumps({"type": "page_manifest", "elements": ELEMENTS}))
        ready = json.loads(ws.receive_text())
        assert ready["type"] == "ready" and ready["engine"] == "adk"
        ws.send_text(
            json.dumps(
                {"type": "audio", "data": "AAA=", "mime_type": "audio/pcm;rate=16000"}
            )
        )
        ws.send_text(
            json.dumps(
                {
                    "type": "tool_result",
                    "id": "c1",
                    "result": {"success": True},
                    "elements": ELEMENTS,
                }
            )
        )
        ws.send_text(json.dumps({"type": "text", "text": "hi"}))
    voice = FakeVoice.instances[0]
    assert voice.kw["elements"] == ELEMENTS
    kinds = [c[0] for c in voice.calls]
    assert kinds[:3] == ["audio", "tool_result", "text"]
    assert kinds[-1] == "close"


def test_model_and_location_defaults(monkeypatch):
    from backend.config import (
        get_fallback_model,
        get_location,
        get_model,
        get_text_model,
    )

    assert get_model() == "gemini-3.8-live"
    assert get_fallback_model() == "gemini-3.8-live"
    assert get_text_model() == "gemini-3.8-flash"
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    assert get_location() == "us"
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-live-extended-thinking")
    assert get_model() == "gemini-3.8-live-extended-thinking"
