# Copyright 2024 Google, LLC. This software is provided as-is, without
# warranty or representation for any use or purpose. Your use of it is
# subject to your agreement with Google.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from agent import SwotAgentDeps, SwotAnalysis
from pydantic_ai import models
import pytest

# Prevent accidental model requests during testing
models.ALLOW_MODEL_REQUESTS = False


class TestSWOTAnalysis:
    """Test the SWOT Analysis data model"""

    def test_swot_analysis_model(self) -> None:
        """Test that the SWOT Analysis model can be instantiated with valid data"""
        analysis = SwotAnalysis(
            strengths=["Strong brand"],
            weaknesses=["High costs"],
            opportunities=["New markets"],
            threats=["Competition"],
            analysis="Test analysis",
        )
        assert isinstance(analysis, SwotAnalysis)
        assert len(analysis.strengths) == 1
        assert len(analysis.weaknesses) == 1
        assert len(analysis.opportunities) == 1
        assert len(analysis.threats) == 1
        assert analysis.analysis == "Test analysis"


class TestSwotAgentDeps:
    """Test the SWOT Agent Dependencies"""

    @pytest.fixture
    def agent_deps(self) -> SwotAgentDeps:
        """Create a basic SwotAgentDeps instance for testing"""
        return SwotAgentDeps()

    def test_agent_initialization(self, agent_deps: SwotAgentDeps) -> None:
        """Test that the agent dependencies are properly initialized"""
        assert agent_deps.tool_history == []
        assert agent_deps.request is None
        assert agent_deps.update_status_func is None

    def test_gemini_client_initialization(self, agent_deps: SwotAgentDeps) -> None:
        """Test Gemini client initialization"""
        # Just verify that the Gemini client exists (could be None or initialized)
        assert hasattr(agent_deps, "client")

    def test_reddit_client_initialization(self, agent_deps: SwotAgentDeps) -> None:
        """Test Reddit client initialization"""
        # Just verify that the reddit client exists (could be None or initialized)
        assert hasattr(agent_deps, "reddit")

    def test_mock_analysis(self, agent_deps: SwotAgentDeps) -> None:
        """Test that the required attributes exist for analysis"""
        # Test SwotAnalysis model structure using model_fields
        required_fields = {
            "strengths",
            "weaknesses",
            "opportunities",
            "threats",
            "analysis",
        }
        model_fields = set(SwotAnalysis.model_fields.keys())
        assert required_fields.issubset(
            model_fields
        ), f"Missing fields: {required_fields - model_fields}"

        # Test agent dependencies
        assert hasattr(agent_deps, "client")
        assert hasattr(agent_deps, "tool_history")
