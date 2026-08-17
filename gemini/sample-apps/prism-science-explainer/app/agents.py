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
"""Factory functions for Prism's sub-agents (real ADK LlmAgents, real models).

Every agent here runs the SAME model (config.MODEL). There is no cheaper second
tier: the gatekeeper, the planner, all five grounded research workers and every
UI generator are the same Gemini 3.7 Flash. The only per-role dial is the
thinking level (config.THINK / MODES[...]["thinking"]).
"""

from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.tools import google_search
from google.genai import types

from app import config, prompts
from app.callbacks import collect_sources, make_timing_callbacks
from app.schemas import ResearchPlan, Scope


def build_gatekeeper() -> LlmAgent:
    before, after = make_timing_callbacks("gatekeeper")
    return LlmAgent(
        name="gatekeeper",
        model=config.make_model(config.MODEL),
        instruction=prompts.GATEKEEPER,
        include_contents="none",
        output_schema=Scope,
        output_key="scope",
        generate_content_config=config.gen_config("gatekeeper"),
        before_agent_callback=before,
        after_agent_callback=after,
    )


def build_planner() -> LlmAgent:
    before, after = make_timing_callbacks("planner")
    return LlmAgent(
        name="planner",
        model=config.make_model(config.MODEL),
        instruction=prompts.PLANNER,
        include_contents="none",
        output_schema=ResearchPlan,
        output_key="plan",
        generate_content_config=config.gen_config("planner"),
        before_agent_callback=before,
        after_agent_callback=after,
    )


def build_worker(i: int) -> LlmAgent:
    return LlmAgent(
        name=f"worker_{i}",
        model=config.make_model(config.MODEL),
        instruction=prompts.worker_instruction(i),
        include_contents="none",
        tools=[google_search],
        output_key=f"finding_{i}",
        after_model_callback=collect_sources,
        # Low temperature: grounded factual extraction should stay faithful to the
        # search results, not paraphrase creatively or drift into invention.
        generate_content_config=config.gen_config("worker", temperature=0.1),
    )


def build_swarm() -> ParallelAgent:
    return ParallelAgent(
        name="research_swarm",
        sub_agents=[build_worker(i) for i in range(config.MAX_WORKERS)],
    )


def build_ui_generator() -> LlmAgent:
    """Freeform mode: writes a full bespoke self-contained HTML document."""
    return LlmAgent(
        name="ui_generator",
        model=config.make_model(config.MODEL),
        instruction=prompts.UI_GENERATOR,
        include_contents="none",
        output_key="html",
        generate_content_config=config.gen_config(
            "ui", temperature=0.4, max_output_tokens=config.UI_MAX_OUTPUT_TOKENS
        ),
    )


def build_ui_filler(name: str, model_id: str, thinking_level) -> LlmAgent:
    """Template mode: writes ONLY the JS payload (PRISM_SPEC + PRISM_SIM) that the
    fixed shell splices in. Much smaller output -> much faster.

    model_id/thinking_level come from MODES[...]; the model is the same for every
    mode, so `thinking_level` is what actually differs between fast and balanced.
    """
    return LlmAgent(
        name=name,
        model=config.make_model(model_id),
        instruction=prompts.UI_FILLER,
        include_contents="none",
        output_key="fill",
        generate_content_config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
            temperature=0.4,
            max_output_tokens=config.FILL_MAX_OUTPUT_TOKENS,
        ),
    )


def build_ui_fixer() -> LlmAgent:
    return LlmAgent(
        name="ui_fixer",
        model=config.make_model(config.MODEL),
        instruction=prompts.UI_FIXER,
        include_contents="none",
        output_key="html",
        generate_content_config=config.gen_config(
            "fixer", max_output_tokens=config.UI_MAX_OUTPUT_TOKENS
        ),
    )
