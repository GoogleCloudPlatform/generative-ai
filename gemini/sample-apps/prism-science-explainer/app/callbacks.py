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
"""Agent callbacks: (1) mine Google Search grounding metadata into session state
so the final explainer can show real inline citations; (2) time each agent
individually — needed because the gatekeeper and planner now run concurrently, so
a single shared wall-time would misrepresent each step's real cost."""

import time

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse


def make_timing_callbacks(name: str):
    """Return (before, after) agent callbacks that record this agent's own
    wall-time into state['dur_<name>']. Distinct per-agent keys avoid the
    last-write-wins merge that a shared dict would suffer under ParallelAgent."""
    start_key = f"_t0_{name}"
    dur_key = f"dur_{name}"

    def before(callback_context: CallbackContext):
        callback_context.state[start_key] = time.time()
        return None

    def after(callback_context: CallbackContext):
        t0 = callback_context.state.get(start_key)
        if t0 is not None:
            callback_context.state[dur_key] = round(time.time() - t0, 2)
        return None

    return before, after


def collect_sources(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> LlmResponse | None:
    """after_model_callback for research workers: append grounded web sources
    (deduped by URI) into state['sources']."""
    gm = getattr(llm_response, "grounding_metadata", None)
    if not gm:
        return None
    chunks = getattr(gm, "grounding_chunks", None) or []

    sources = callback_context.state.get("sources") or []
    seen = {s.get("uri") for s in sources}
    for ch in chunks:
        web = getattr(ch, "web", None)
        if not web:
            continue
        uri = getattr(web, "uri", "") or ""
        title = getattr(web, "title", "") or ""
        if uri and uri not in seen:
            sources.append({"uri": uri, "title": title})
            seen.add(uri)
    callback_context.state["sources"] = sources
    return None
