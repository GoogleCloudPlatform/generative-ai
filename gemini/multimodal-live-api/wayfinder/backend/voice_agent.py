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

"""Voice transport: an ADK agent running on the Gemini Live API.

One ADK `LlmAgent` per browser voice connection, run with `Runner.run_live()`.

- UI actions are ADK tools that run in the browser and return the real
  outcome (see `browser_tools.py`).
- Knowledge search runs on the server through Vertex AI Search.
- The default model is the GA Gemini 3.8 Live model. If you configure
  Gemini 3.8 Live Extended Thinking, the agent uses asynchronous
  (NON_BLOCKING) function calling, leaves proactive audio to the model, and
  sets a thinking level. If the configured model can't start a session, the
  agent falls back to `GEMINI_FALLBACK_MODEL`.
- ADK handles `go_away` reconnects with session resumption and applies
  context window compression from `RunConfig`.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.tools import FunctionTool
from google.genai import types

from .browser_tools import BrowserBridge, build_dom_tools
from .config import (
    get_fallback_model,
    get_live_affective_dialog,
    get_live_async_search,
    get_live_context_compression,
    get_live_proactive_audio,
    get_live_thinking_level,
    get_live_voice,
    get_location,
    get_model,
    get_project_id,
)
from .page_map import format_element_list
from .rag import RagCoordinator
from .system_instruction import (
    SYSTEM_INSTRUCTION_GROUNDED,
    SYSTEM_INSTRUCTION_VISION_ONLY,
)

logger = logging.getLogger(__name__)

APP_NAME = "wayfinder-voice"
SendFn = Callable[[dict], Awaitable[None]]


def is_async_only_model(model: str) -> bool:
    """Gemini 3.8 Live Extended Thinking supports only NON_BLOCKING function
    calls, no response scheduling, and always-on proactive audio.
    """
    return "extended-thinking" in (model or "")


def build_search_tool(
    coordinator: RagCoordinator, model: str, async_search: bool = True
) -> FunctionTool:
    """Builds the knowledge-base search tool for the voice agent."""

    async def search_knowledge_base(query: str) -> dict:
        """Search the product documentation for how-to, best-practice, or
        troubleshooting guidance. Cite the source title in your answer.

        Args:
            query: Natural-language description of what the user wants to know.
        """
        return await coordinator.asearch_payload(query, top_k=5)

    tool = FunctionTool(func=search_knowledge_base)
    if is_async_only_model(model):
        tool.behavior = types.Behavior.NON_BLOCKING  # required; scheduling unsupported
    elif async_search:
        # Keep talking while the search runs; react when the model is idle.
        tool.behavior = types.Behavior.NON_BLOCKING
        tool.response_scheduling = types.FunctionResponseScheduling.WHEN_IDLE
    return tool


def build_voice_agent(
    coordinator: RagCoordinator,
    bridge: BrowserBridge,
    grounded: bool,
    model: str | None = None,
    async_search: bool | None = None,
) -> LlmAgent:
    """Builds the live voice agent with browser UI tools and optional search."""
    model = model or get_model()
    base = SYSTEM_INSTRUCTION_GROUNDED if grounded else SYSTEM_INSTRUCTION_VISION_ONLY
    element_list = format_element_list(bridge.elements)
    instruction = (
        base
        + ("\n\n" + element_list if element_list else "")
        + (
            "\n\nEach action returns its real outcome from the page. If success is false, "
            "read the error and fix the call (for example pick a listed option) instead of "
            "repeating it. page_changes lists elements whose state changed or appeared."
        )
    )
    async_only = is_async_only_model(model)
    tools: list = build_dom_tools(lambda _ctx: bridge, non_blocking=async_only)
    if grounded:
        if async_search is None:
            async_search = get_live_async_search()
        tools.insert(0, build_search_tool(coordinator, model, async_search))
    generate_config = None
    if async_only:
        generate_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=get_live_thinking_level()
            )
        )
    return LlmAgent(
        name="wayfinder_voice",
        model=model,
        # A callable instruction bypasses ADK's {state} templating, so braces
        # in page labels can't be misread as template variables.
        instruction=lambda _ctx: instruction,
        tools=tools,
        generate_content_config=generate_config,
    )


def build_run_config(model: str, optional_features: bool = True) -> RunConfig:
    """Builds the ADK RunConfig for a live voice session."""
    kwargs: dict = dict(  # noqa: C408  # pylint: disable=use-dict-literal
        streaming_mode=StreamingMode.BIDI,
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=get_live_voice()
                )
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=types.SessionResumptionConfig(),
    )
    if get_live_context_compression():
        kwargs["context_window_compression"] = types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow()
        )
    if optional_features:
        # Extended Thinking keeps proactive audio permanently on and rejects
        # an explicit setting, so only send it to other models.
        if get_live_proactive_audio() and not is_async_only_model(model):
            kwargs["proactivity"] = types.ProactivityConfig(proactive_audio=True)
        if get_live_affective_dialog():
            kwargs["enable_affective_dialog"] = True
    return RunConfig(**kwargs)


def event_to_messages(event: Any) -> list[dict]:
    """Translate an ADK live Event into widget messages."""
    out: list[dict] = []
    if getattr(event, "interrupted", False):
        out.append({"type": "interrupted"})
    t = getattr(event, "input_transcription", None)
    if t and t.text:
        out.append(
            {
                "type": "input_transcript",
                "text": t.text,
                "finished": bool(getattr(t, "finished", False)),
            }
        )
    t = getattr(event, "output_transcription", None)
    if t and t.text and getattr(event, "partial", None) is not False:
        # ADK also emits one aggregated (partial=False) transcription per
        # turn; the widget already has the streamed chunks.
        out.append(
            {
                "type": "output_transcript",
                "text": t.text,
                "finished": bool(getattr(t, "finished", False)),
            }
        )
    content = getattr(event, "content", None)
    for part in content.parts if content and content.parts else []:
        blob = part.inline_data
        if blob and (blob.mime_type or "").startswith("audio/"):
            out.append(
                {
                    "type": "audio",
                    "data": base64.b64encode(blob.data).decode("ascii"),
                    "mime_type": blob.mime_type,
                }
            )
    if getattr(event, "turn_complete", False):
        out.append({"type": "turn_complete"})
    return out


def is_idle(event: Any) -> bool:
    """True when the model has finished all work for the current request.

    With asynchronous reasoning, turn_complete no longer means idle; use
    interaction_status when the server sends it.
    """
    status = getattr(event, "interaction_status", None)
    if status is not None:
        return status == types.InteractionStatus.IDLE
    return bool(getattr(event, "turn_complete", False))


class VoiceSession:  # pylint: disable=too-many-instance-attributes
    """One browser voice connection running an ADK agent in live mode."""

    def __init__(  # pylint: disable=too-many-arguments  # keyword-only
        self,
        *,
        session_service: Any,
        coordinator: RagCoordinator,
        grounded: bool,
        send: SendFn,
        elements: list,
        user_id: str,
    ) -> None:
        get_project_id()  # ADK's Vertex client reads project/location from env
        get_location()
        self._session_service = session_service
        self._send = send
        self.user_id = user_id
        self.session_id = uuid.uuid4().hex
        self.bridge = BrowserBridge(send, elements)
        self._coordinator, self._grounded = coordinator, grounded
        self.model = get_model()
        self._build(async_search=None)
        self.queue = LiveRequestQueue()
        self._closed = False
        # Typed turns sent before the model produced any output; replayed if a
        # fallback restarts the session with a fresh queue.
        self._started = False
        self._early_turns: list[types.Content] = []

    def _build(self, async_search: bool | None) -> None:
        self.agent = build_voice_agent(
            self._coordinator,
            self.bridge,
            self._grounded,
            model=self.model,
            async_search=async_search,
        )
        self.runner = Runner(
            agent=self.agent, app_name=APP_NAME, session_service=self._session_service
        )

    async def run(self, on_ready: Callable[[], Awaitable[None]] | None = None) -> None:
        """Stream agent events to the browser until closed.

        If the session fails before producing any output, retries without
        optional Live features, then with the fallback model.
        """
        await self._session_service.create_session(
            app_name=APP_NAME, user_id=self.user_id, session_id=self.session_id
        )
        fallbacks: list[tuple[str, dict]] = [
            (
                "without optional Live features",
                {"optional": False, "model": self.model},
            ),
        ]
        fallback_model = get_fallback_model()
        if self.model != fallback_model:
            fallbacks.append(
                (
                    f"with the fallback model {fallback_model}",
                    {"optional": False, "model": fallback_model},
                )
            )
        optional = True
        while not self._closed:
            got_event = False
            try:
                async for event in self.runner.run_live(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    live_request_queue=self.queue,
                    run_config=build_run_config(self.model, optional),
                ):
                    if not got_event:
                        got_event = True
                        self._started = True
                        self._early_turns.clear()
                        logger.info("Voice session running on %s", self.model)
                        if on_ready:
                            await on_ready()
                            on_ready = None
                    if getattr(event, "interrupted", False) or is_idle(event):
                        self.bridge.new_turn()
                    for msg in event_to_messages(event):
                        await self._send(msg)
                return
            except asyncio.CancelledError:  # pylint: disable=try-except-raise  # never retry a cancel
                raise
            except Exception as e:  # pylint: disable=broad-exception-caught  # retry with fallbacks
                if got_event or self._closed or not fallbacks:
                    raise
                label, opts = fallbacks.pop(0)
                logger.warning(
                    "Voice session failed to start on %s (%s); retrying %s.",
                    self.model,
                    e,
                    label,
                )
                optional = opts["optional"]
                self.model = opts["model"]
                self.queue = LiveRequestQueue()
                for content in self._early_turns:
                    self.queue.send_content(content)
                self._build(async_search=False)

    # ---- Browser -> agent ----

    def send_text(self, text: str) -> None:
        """Sends a typed user turn to the agent."""
        self.bridge.new_turn()
        content = types.Content(role="user", parts=[types.Part(text=text)])
        if not self._started:
            self._early_turns.append(content)
        self.queue.send_content(content)

    def send_audio(self, data: bytes, mime_type: str = "audio/pcm;rate=16000") -> None:
        """Streams a chunk of microphone audio to the agent."""
        self.queue.send_realtime(types.Blob(data=data, mime_type=mime_type))

    def send_image(self, data: bytes) -> None:
        """Streams a JPEG page snapshot to the agent."""
        self.queue.send_realtime(types.Blob(data=data, mime_type="image/jpeg"))

    def tool_result(self, call_id: str, result: dict, elements: list | None) -> None:
        """Delivers a browser tool result to the waiting tool call."""
        self.bridge.resolve(call_id, result, elements)

    def update_elements(self, elements: list) -> None:
        """Replaces the current page element map."""
        self.bridge.update_elements(elements)

    def close(self) -> None:
        """Stops the session and closes the request queue."""
        self._closed = True
        self.queue.close()
