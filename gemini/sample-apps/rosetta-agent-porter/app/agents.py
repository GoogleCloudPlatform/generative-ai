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
"""Factory functions for Rosetta's sub-agents (real ADK LlmAgents, real models).

Always CALL a factory to get a fresh instance — never reuse an agent object under
two parents (ADK raises "agent already has a parent").
"""

from google.adk.agents import LlmAgent, ParallelAgent

from app import config, prompts, schemas


# --------------------------------------------------------------------------- #
# Stage 1 — intake
# --------------------------------------------------------------------------- #
def build_intake() -> LlmAgent:
    return LlmAgent(
        name="intake",
        model=config.make_model("intake"),  # 3.7 Flash @ LOW thinking
        instruction=prompts.INTAKE,
        include_contents="none",
        output_schema=schemas.RepoScan,
        output_key="scope",
        generate_content_config=config.gen_config("intake"),
    )


# --------------------------------------------------------------------------- #
# Stage 2 — analysis swarm (6 parallel readers, one facet each)
# --------------------------------------------------------------------------- #
def _analyst(name: str, instruction: str, out_schema, out_key: str) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=config.make_model(name),  # 3.7 Flash; thinking per ROLE_THINKING
        instruction=instruction,
        include_contents="none",
        output_schema=out_schema,
        output_key=out_key,
        generate_content_config=config.gen_config(name),
    )


def build_graph_analyst() -> LlmAgent:
    return _analyst(
        "graph_analyst", prompts.GRAPH_ANALYST, schemas.GraphAnalysis, "analysis_graph"
    )


def build_prompt_analyst() -> LlmAgent:
    return _analyst(
        "prompt_analyst",
        prompts.PROMPT_ANALYST,
        schemas.PromptAnalysis,
        "analysis_prompts",
    )


def build_tool_analyst() -> LlmAgent:
    return _analyst(
        "tool_analyst", prompts.TOOL_ANALYST, schemas.ToolAnalysis, "analysis_tools"
    )


def build_state_analyst() -> LlmAgent:
    return _analyst(
        "state_analyst", prompts.STATE_ANALYST, schemas.StateAnalysis, "analysis_state"
    )


def build_model_analyst() -> LlmAgent:
    return _analyst(
        "model_analyst", prompts.MODEL_ANALYST, schemas.ModelAnalysis, "analysis_models"
    )


def build_input_harvester() -> LlmAgent:
    return _analyst(
        "input_harvester", prompts.INPUT_HARVESTER, schemas.EvalInputs, "eval_inputs"
    )


def build_analysis_swarm() -> ParallelAgent:
    """The parallel analysis swarm — distinct output_keys avoid state races."""
    return ParallelAgent(
        name="analysis_swarm",
        sub_agents=[
            build_graph_analyst(),
            build_prompt_analyst(),
            build_tool_analyst(),
            build_state_analyst(),
            build_model_analyst(),
            build_input_harvester(),
        ],
    )


# --------------------------------------------------------------------------- #
# Stage 3+ — port planner, codegen, fixer (the SMART "brain")
# --------------------------------------------------------------------------- #
from google.adk.tools import FunctionTool  # noqa: E402

from app import tools as _tools  # noqa: E402


def _provider(template: str, keys: list[str]):
    """Return an InstructionProvider (callable) that substitutes ONLY our named
    placeholders via str.replace. Passing a callable makes ADK set
    bypass_state_injection=True, so literal `{...}` in embedded code examples (the
    ADK cheat-sheet) are left untouched instead of parsed as state variables."""

    def _inst(ctx) -> str:
        s = template
        state = getattr(ctx, "state", {}) or {}
        for k in keys:
            s = s.replace("{" + k + "}", str(state.get(k, "")))
        return s

    return _inst


def build_port_planner() -> LlmAgent:
    """Pure structured planner (output_schema=PortPlan). Static mapping guidance in
    the prompt; kept tool-free so the typed IR is reliable."""
    return LlmAgent(
        name="port_planner",
        model=config.make_model("port_planner"),  # SMART
        instruction=prompts.PORT_PLANNER,
        include_contents="none",
        output_schema=schemas.PortPlan,
        output_key="port_plan",
        generate_content_config=config.gen_config(
            "port_planner", max_output_tokens=config.PLAN_MAX_TOKENS
        ),
    )


def build_codegen() -> LlmAgent:
    """Delimited-file code generator. No output_schema (raw code is more robust as
    delimited text than JSON-escaped). Gets the on-demand skill-reference tool."""
    kw = {}
    if _tools.skill_reference_available():
        kw["tools"] = [FunctionTool(_tools.read_skill_reference)]
    return LlmAgent(
        name="codegen",
        model=config.make_model("codegen"),  # SMART
        instruction=_provider(
            prompts.CODEGEN,
            [
                "framework",
                "agent_summary",
                "port_plan_block",
                "prompts_block",
                "analyses_block",
            ],
        ),
        include_contents="none",
        output_key="generated_raw",
        generate_content_config=config.gen_config(
            "codegen", temperature=0.2, max_output_tokens=config.CODEGEN_MAX_TOKENS
        ),
        **kw,
    )


def build_fixer() -> LlmAgent:
    return LlmAgent(
        name="fixer",
        model=config.make_model("fixer"),  # SMART
        instruction=_provider(prompts.FIXER, ["verdict_errors", "broken_block"]),
        include_contents="none",
        output_key="fixed_raw",
        generate_content_config=config.gen_config(
            "fixer", max_output_tokens=config.CODEGEN_MAX_TOKENS
        ),
    )
