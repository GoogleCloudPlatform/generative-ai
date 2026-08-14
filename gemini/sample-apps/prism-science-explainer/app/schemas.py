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
"""Typed contracts passed between Prism's agents (also used as ADK output_schema)."""

from typing import Literal

from pydantic import BaseModel, Field


class Scope(BaseModel):
    """Gatekeeper decision."""

    decision: Literal["ok", "reject", "unsafe"] = Field(
        description="'ok' for any real science/STEM concept OR everyday natural-world "
        "question that can be taught; 'reject' for non-science (opinions, news, shopping, "
        "app-build, chit-chat, gibberish); 'unsafe' for genuinely harmful requests."
    )
    concept: str = Field(
        description="The concept normalized to a clear question or noun phrase (if ok)."
    )
    level: Literal["everyday", "intermediate", "advanced"] = Field(
        default="intermediate",
        description="Audience level: 'everyday' (a curious layperson's day-to-day question "
        "like 'why is the sky blue?'), 'intermediate' (high-school / early-college), or "
        "'advanced' (specialist / university+). Drives how deep/technical the explainer is.",
    )
    reason: str = Field(
        default="", description="One short sentence explaining the decision."
    )


class Subtopic(BaseModel):
    angle: str = Field(
        description="Short label for this research angle, e.g. 'intuition', 'the math', "
        "'a worked example', 'common misconceptions', 'history'."
    )
    query: str = Field(description="A focused web-search query to research this angle.")


class ResearchPlan(BaseModel):
    concept: str
    key_interaction: str = Field(
        description="The single most illuminating INTERACTIVE idea to build the explainer "
        "around — one dominant draggable parameter or live simulation."
    )
    viz_hint: Literal["canvas-sim", "svg-diagram", "chart", "three-3d"] = Field(
        default="canvas-sim",
        description="How to visualize it. The default fast/balanced modes render on a "
        "Canvas2D shell, so prefer 'canvas-sim'; 'svg-diagram'/'chart'/'three-3d' are fully "
        "honored only in freeform mode.",
    )
    subtopics: list[Subtopic] = Field(
        description="Exactly 5 research angles to investigate in parallel (see the planner)."
    )


class Source(BaseModel):
    title: str = ""
    uri: str = ""


class UIVerdict(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
