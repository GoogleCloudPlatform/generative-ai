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

"""UI actions as ADK tools that run in the user's browser.

Each tool call is sent to the widget, which performs it on the live page and
reports the real outcome (success, new state, or an error with the valid
options) plus the page state afterwards. The agent observes what actually
happened instead of assuming success. Used by both the voice and text agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable

from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from .page_map import format_element, sanitize_page_text

logger = logging.getLogger(__name__)

# How long a UI tool waits for the browser to report the outcome.
BROWSER_RESULT_TIMEOUT_S = 8.0
# Cap on changed elements echoed back to the model per action.
MAX_CHANGED_ELEMENTS = 12

SendFn = Callable[[dict], Awaitable[None]]


def _element_state(el: dict) -> tuple:
    selected = next(
        (o.get("value") for o in el.get("options") or [] if o.get("selected")), None
    )
    return (el.get("value"), el.get("checked"), selected)


def summarize_page_changes(before: list, after: list) -> list[str]:
    """Element-list lines that are new or whose value/state changed."""
    old = {el.get("selector"): _element_state(el) for el in before or []}
    lines = []
    for el in after or []:
        sel = el.get("selector")
        if sel not in old or old[sel] != _element_state(el):
            lines.append(format_element(el).strip())
        if len(lines) >= MAX_CHANGED_ELEMENTS:
            break
    return lines


class BrowserBridge:
    """Sends UI tool calls to the widget and awaits the real outcome.

    `send` delivers a `{"type": "tool_call", "calls": [...]}` message to the
    browser (over the voice WebSocket, or as an SSE event for text).
    """

    def __init__(
        self,
        send: SendFn,
        elements: list | None = None,
        timeout: float = BROWSER_RESULT_TIMEOUT_S,
        origin: str = "",
    ):
        self._send = send
        self._timeout = timeout
        self._pending: dict[str, asyncio.Future] = {}
        self._turn_sigs: set[str] = set()
        self.elements: list = list(elements or [])
        self.origin = origin

    def new_turn(self) -> None:
        """Forget per-turn de-duplication (new user input or the model went idle)."""
        self._turn_sigs.clear()

    def update_elements(self, elements: list) -> None:
        """Replace the cached page element list."""
        self.elements = list(elements or [])

    async def call(self, name: str, args: dict) -> dict:
        """Send one UI action to the browser and return its reported outcome."""
        sig = name + "|" + json.dumps(args, sort_keys=True)
        if sig in self._turn_sigs:
            return {
                "success": True,
                "note": "Already done in this turn. Do not repeat it.",
            }
        self._turn_sigs.add(sig)

        call_id = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self._pending[call_id] = future
        try:
            await self._send(
                {
                    "type": "tool_call",
                    "calls": [{"id": call_id, "name": name, "args": args}],
                }
            )
            result, elements = await asyncio.wait_for(future, timeout=self._timeout)
        except TimeoutError:
            logger.warning("No browser result for %s within %.1fs", name, self._timeout)
            return {
                "success": False,
                "error": "The page did not report a result in time. "
                "Ask the user to check the page.",
            }
        finally:
            self._pending.pop(call_id, None)

        out = dict(result or {})
        if elements:
            changes = summarize_page_changes(self.elements, elements)
            self.elements = elements
            if changes:
                out["page_changes"] = changes
        return out

    def resolve(self, call_id: str, result: dict, elements: list | None) -> bool:
        """Deliver a browser result. Returns False if no call is waiting."""
        future = self._pending.get(call_id)
        if future and not future.done():
            future.set_result((self._clean_result(result), elements or []))
            return True
        if elements:
            self.update_elements(elements)
        return False

    @staticmethod
    def _clean_result(result: dict | None) -> dict:
        """Keep only small, expected fields from the (untrusted) browser."""
        result = result if isinstance(result, dict) else {}
        out: dict = {"success": bool(result.get("success", False))}
        for key in (
            "state",
            "value",
            "selected_value",
            "selected_text",
            "note",
            "error",
        ):
            if key in result and result[key] is not None:
                out[key] = sanitize_page_text(result[key], 120)
        if isinstance(result.get("options"), list):
            out["options"] = [sanitize_page_text(o, 40) for o in result["options"][:30]]
        return out


BridgeResolver = Callable[[ToolContext | None], BrowserBridge | None]

_NO_PAGE = {"success": False, "error": "No page is connected to carry out this action."}


def build_dom_tools(
    resolve_bridge: BridgeResolver, non_blocking: bool = False
) -> list[FunctionTool]:
    """The five UI tools. `resolve_bridge` finds the bridge for the calling session.

    `non_blocking=True` marks them NON_BLOCKING for Live models that only
    support asynchronous function calling.
    """

    async def _run(tool_context: ToolContext | None, name: str, args: dict) -> dict:
        bridge = resolve_bridge(tool_context)
        if bridge is None:
            return dict(_NO_PAGE)
        return await bridge.call(name, args)

    async def click_element(
        selector: str,
        description: str,
        desired_state: str = "",
        tool_context: ToolContext = None,
    ) -> dict:
        """Click a button, tab, link, or toggle on the page.

        Args:
            selector: Exact CSS selector from the element list.
            description: Short human-readable description of the target.
            desired_state: For checkboxes/toggles only: "ON" or "OFF". The click
                is skipped if the toggle is already in that state.
        """
        args = {"selector": selector, "description": description}
        if desired_state:
            args["desired_state"] = desired_state.upper()
        return await _run(tool_context, "click_element", args)

    async def type_text(
        selector: str, text: str, description: str, tool_context: ToolContext = None
    ) -> dict:
        """Type text into an input or textarea (replaces its current value).

        Args:
            selector: Exact CSS selector from the element list.
            text: The text to enter.
            description: Which field is being filled.
        """
        return await _run(
            tool_context,
            "type_text",
            {"selector": selector, "text": text, "description": description},
        )

    async def select_option(
        selector: str, value: str, description: str, tool_context: ToolContext = None
    ) -> dict:
        """Choose an option in a dropdown (<select>) by its option value.

        Args:
            selector: Exact CSS selector of the dropdown from the element list.
            value: The option value to select (from the listed options).
            description: What is being changed.
        """
        return await _run(
            tool_context,
            "select_option",
            {"selector": selector, "value": value, "description": description},
        )

    async def highlight_element(
        selector: str, description: str, tool_context: ToolContext = None
    ) -> dict:
        """Visually point out an element WITHOUT changing it.

        Args:
            selector: Exact CSS selector from the element list.
            description: What the element is.
        """
        return await _run(
            tool_context,
            "highlight_element",
            {"selector": selector, "description": description},
        )

    async def scroll_to_element(
        direction: str, description: str, tool_context: ToolContext = None
    ) -> dict:
        """Scroll the page "up" or "down" to reveal off-screen content.

        Args:
            direction: "up" or "down".
            description: What you are looking for.
        """
        return await _run(
            tool_context,
            "scroll_to_element",
            {"direction": direction, "description": description},
        )

    tools = [
        FunctionTool(func=f)
        for f in (
            click_element,
            type_text,
            select_option,
            highlight_element,
            scroll_to_element,
        )
    ]
    if non_blocking:
        for t in tools:
            t.behavior = types.Behavior.NON_BLOCKING
    return tools
