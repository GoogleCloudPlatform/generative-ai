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
"""Unit tests for the typed contracts passed between agents."""

import pytest
from pydantic import ValidationError

from app.schemas import ResearchPlan, Scope, Subtopic, UIVerdict


def test_scope_decision_literal():
    assert Scope(decision="ok", concept="entropy").decision == "ok"
    with pytest.raises(ValidationError):
        Scope(decision="maybe", concept="x")  # not in {ok, reject, unsafe}


def test_scope_level():
    # default level is intermediate; the field is a constrained literal
    assert Scope(decision="ok", concept="entropy").level == "intermediate"
    assert Scope(decision="ok", concept="sky", level="everyday").level == "everyday"
    with pytest.raises(ValidationError):
        Scope(decision="ok", concept="x", level="expert")  # not a valid level


def test_research_plan_roundtrips():
    plan = ResearchPlan(
        concept="How does a neural network learn?",
        key_interaction="Drag the learning rate and watch the weight descend.",
        viz_hint="canvas-sim",
        subtopics=[Subtopic(angle="the math", query="gradient descent loss")],
    )
    d = plan.model_dump()
    assert ResearchPlan(**d).subtopics[0].angle == "the math"
    with pytest.raises(ValidationError):
        ResearchPlan(  # viz_hint is now a constrained literal
            concept="c", key_interaction="k", viz_hint="hologram", subtopics=[]
        )


def test_ui_verdict():
    assert UIVerdict(ok=True).errors == []
    v = UIVerdict(ok=False, errors=["missing </html>"])
    assert not v.ok and v.errors
