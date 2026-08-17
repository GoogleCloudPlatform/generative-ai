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
"""Typed contracts passed between Rosetta's agents (also used as ADK output_schema).

Design notes:
  * Kept moderately typed — nested models where structure helps the generator,
    plain str/lists where over-specifying would hurt extraction reliability.
  * Every field has a Field(description=...) — those descriptions are part of the
    prompt the model sees when producing structured output, so they are written
    to *instruct*, not just document.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app import config

Framework = Literal[
    "langgraph",
    "langchain",
    "crewai",
    "autogen",
    "llamaindex",
    "plain_python",
    "unknown",
]
Difficulty = Literal["clean", "medium", "tricky"]
AgentKind = Literal[
    "LlmAgent", "SequentialAgent", "ParallelAgent", "LoopAgent", "BaseAgent"
]


# --------------------------------------------------------------------------- #
# Stage 1 — intake / framework detection
# --------------------------------------------------------------------------- #
class RepoScan(BaseModel):
    """Framework detection + triage decision for a source repo."""

    framework: Framework = Field(description="Detected source framework.")
    confidence: float = Field(description="0..1 confidence in the framework call.")
    decision: Literal["ok", "reject", "unsafe"] = Field(
        description="'ok' = a real agent repo to port; 'reject' = not an agent repo "
        "(static site, plain library, data-science notebooks); 'unsafe' = malicious "
        "code (malware, credential exfiltration) — refuse."
    )
    agent_summary: str = Field(
        default="",
        description="1-2 sentences: what this agent does, end to end.",
    )
    entrypoints: list[str] = Field(
        default_factory=list,
        description="Relative paths of the file(s) that define the graph/agent entrypoint.",
    )
    files_to_analyze: list[str] = Field(
        default_factory=list,
        description="Relative paths of the source files worth deep analysis "
        "(graph, state, prompts, tools, config) — bounded, most-important first.",
    )
    reason: str = Field(
        default="", description="One short sentence explaining the decision."
    )


# --------------------------------------------------------------------------- #
# Stage 2 — parallel analysis swarm (one facet per worker)
# --------------------------------------------------------------------------- #
class GraphEdge(BaseModel):
    source: str = Field(description="Source node name.")
    target: str = Field(description="Target node name, or END.")
    condition: str = Field(
        default="", description="Condition for a conditional edge, if any."
    )


class GraphAnalysis(BaseModel):
    """Control-flow / topology of the source agent."""

    nodes: list[str] = Field(
        description="All node/agent names in execution order where possible."
    )
    edges: list[GraphEdge] = Field(
        default_factory=list, description="Edges between nodes."
    )
    entrypoint: str = Field(default="", description="The start node.")
    control_flow: Literal["linear", "branching", "cyclic", "hierarchical"] = Field(
        description="Dominant control-flow shape."
    )
    fan_out: list[str] = Field(
        default_factory=list,
        description="Nodes that spawn parallel/dynamic work (Send, asyncio.gather, "
        "map-reduce, sub-agent delegation) — the tricky-to-port bits.",
    )
    loops: list[str] = Field(
        default_factory=list,
        description="Reflection / ReAct / retry loops (node<->tools cycles).",
    )
    notes: str = Field(
        default="", description="Anything a porter must know about the topology."
    )


class PromptSpec(BaseModel):
    owner: str = Field(description="Which node/agent uses this prompt.")
    name: str = Field(description="A short identifier for the prompt.")
    text: str = Field(description="The full prompt text (verbatim if possible).")


class PromptAnalysis(BaseModel):
    prompts: list[PromptSpec] = Field(default_factory=list)


class ToolSpec(BaseModel):
    name: str = Field(description="Tool/function name.")
    kind: Literal["search", "reflection", "mcp", "retrieval", "handoff", "custom"] = (
        Field(description="Category of tool.")
    )
    used_by: str = Field(default="", description="Which node/agent binds this tool.")
    summary: str = Field(default="", description="What it does + notable args.")


class ToolAnalysis(BaseModel):
    tools: list[ToolSpec] = Field(default_factory=list)


class ReducerSpec(BaseModel):
    channel: str = Field(description="State field / channel name.")
    kind: Literal["override", "accumulate", "default"] = Field(
        description="'accumulate' = append/operator.add/add_messages (reduce); "
        "'override' = replace; 'default' = plain last-write."
    )


class StateAnalysis(BaseModel):
    """State objects + reducer semantics (drives output_key vs accumulation mapping)."""

    state_objects: list[str] = Field(
        default_factory=list, description="State/TypedDict/schema names."
    )
    fields: list[str] = Field(
        default_factory=list,
        description="Notable state field names across the schemas.",
    )
    reducers: list[ReducerSpec] = Field(default_factory=list)
    isolated_channels: list[str] = Field(
        default_factory=list,
        description="Separate message channels/contexts per agent tier (e.g. "
        "messages vs supervisor_messages vs researcher_messages).",
    )
    notes: str = Field(default="")


class RoleModel(BaseModel):
    role: str = Field(
        description="Which step/agent (e.g. researcher, summarizer, report)."
    )
    model: str = Field(description="Model id used for that role in the source.")
    notes: str = Field(default="", description="temperature/max_tokens/etc if notable.")


class ModelAnalysis(BaseModel):
    roles: list[RoleModel] = Field(default_factory=list)
    knobs: list[str] = Field(
        default_factory=list,
        description="Config knobs: concurrency cap, max iterations, search API, "
        "recursion limit, etc. as 'name=value' strings.",
    )
    search_api: str = Field(
        default="", description="Web-search backend, if any (tavily/openai/...)."
    )


class ExampleInput(BaseModel):
    text: str = Field(
        description="A concrete example input/query a user would send the agent."
    )
    source: Literal[
        "readme", "tests", "eval", "notebook", "docstring", "synthesized"
    ] = Field(description="Where this input came from in the repo (or 'synthesized').")


class EvalInputs(BaseModel):
    """Real example inputs mined from the repo (fidelity-eval seeds)."""

    inputs: list[ExampleInput] = Field(default_factory=list)
    needs_synthesis: bool = Field(
        default=False,
        description="True if the repo had no usable example inputs and they must be synthesized.",
    )


# --------------------------------------------------------------------------- #
# Stage 3 — port plan / IR
# --------------------------------------------------------------------------- #
class Mapping(BaseModel):
    source: str = Field(
        description="Source-framework construct (e.g. 'asyncio.gather fan-out')."
    )
    target: str = Field(
        description="Chosen ADK equivalent (e.g. 'ParallelAgent + concurrency cap')."
    )
    difficulty: Difficulty = Field(description="clean | medium | tricky.")
    rationale: str = Field(
        default="", description="Why this ADK idiom; note any caveat."
    )


class AgentSpec(BaseModel):
    name: str = Field(description="Agent name (snake_case).")
    kind: AgentKind = Field(description="ADK agent class.")
    model_role: Literal["smart", "fast", "none"] = Field(
        # Bound from config, not typed literally: this description is part of the
        # JSON schema sent to the planner, so a stale name here reaches the model.
        description=(
            f"'smart' = {config.MODEL_SMART_NAME}, 'fast' = {config.MODEL_FAST_NAME}, "
            "'none' = code-only (BaseAgent)."
        )
    )
    purpose: str = Field(
        description="One line: what this agent does in the ported pipeline."
    )
    tools: list[str] = Field(
        default_factory=list, description="Tool names it binds (e.g. google_search)."
    )
    output_key: str = Field(default="", description="session.state key it writes.")
    output_schema: str = Field(
        default="", description="Structured-output schema name, if any."
    )
    sub_agents: list[str] = Field(
        default_factory=list, description="Names of child agents (for composites)."
    )


class PortPlan(BaseModel):
    """The intermediate representation the code generator builds from."""

    target_name: str = Field(
        description="Ported project name (lowercase-hyphen, <=26 chars)."
    )
    summary: str = Field(description="2-3 sentences describing the ported ADK design.")
    root_kind: AgentKind = Field(description="Top-level orchestration class.")
    agents: list[AgentSpec] = Field(description="The full ADK agent roster.")
    state_keys: list[str] = Field(
        default_factory=list, description="session.state keys used."
    )
    tools: list[str] = Field(
        default_factory=list, description="All ADK tools the port needs."
    )
    files: list[str] = Field(
        default_factory=list,
        description="Planned file paths under app/ (e.g. app/agent.py, app/agents.py, ...).",
    )
    mappings: list[Mapping] = Field(
        description="The full source->ADK concept-mapping table."
    )
    risks: list[Mapping] = Field(
        default_factory=list,
        description="The 'tricky' mappings, restated with the chosen ADK idiom + caveat.",
    )


# --------------------------------------------------------------------------- #
# Stage 4 — codegen + verify
# --------------------------------------------------------------------------- #
class PortedFile(BaseModel):
    path: str = Field(description="Relative path, e.g. app/agent.py.")
    content: str = Field(description="Full file content.")


class GeneratedProject(BaseModel):
    files: list[PortedFile] = Field(
        description="Every source file of the ported ADK project."
    )


class PortVerdict(BaseModel):
    ok: bool
    errors: list[str] = Field(
        default_factory=list, description="syntax/compile/lint/import errors."
    )


# --------------------------------------------------------------------------- #
# Stage 5 — fidelity eval
# --------------------------------------------------------------------------- #
class EvalCase(BaseModel):
    input: str
    verdict: Literal["pass", "partial", "fail"]
    score: float = Field(description="0..1 per-case score.")
    rationale: str = Field(default="")


class FidelityReport(BaseModel):
    score: float = Field(description="Aggregate fidelity 0..1.")
    cases: list[EvalCase] = Field(default_factory=list)
    notes: list[str] = Field(
        default_factory=list,
        description="Verified tricky-mapping annotations (e.g. 'dynamic fan-out verified').",
    )
