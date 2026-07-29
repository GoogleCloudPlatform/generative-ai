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

import pytest
import asyncio
import logging
from unittest.mock import MagicMock, patch
from google.adk.tools import ToolContext
from app.state_schema import ComplianceStep
from app.fallback_handler import invoke_resilient_compliance_check

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_tool_context():
    """Fixture initializing case checkpoints."""
    context = MagicMock(spec=ToolContext)
    context.state = {
        "case_id": "test-resilience-case",
        "current_step": ComplianceStep.EXTRACTED,
        "contract_details": {
            "contract_value": 250000.0,
            "contractor_name": "Standard Corp",
            "liability_limit": "Capped liability limits",
            "term_length_years": 2,
            "insurance_coverage": 2000000.0,
            "has_termination_clause": True,
        },
        "risk_assessment": {"risk_tier": "LOW", "risk_factors": []},
        "compliance_verdict": {},
        "pending_signals": [],
        "trace_logs": []
    }
    return context


@pytest.mark.asyncio
async def test_invoke_resilient_compliance_check_success(mock_tool_context):
    # Mock A2A checker to return immediate success verdict
    mock_response = {
        "status": "success",
        "verdict": {"passed": True, "violations": []}
    }
    
    with patch("app.fallback_handler.invoke_a2a_compliance_check", return_value=mock_response):
        res = await invoke_resilient_compliance_check(mock_tool_context, timeout_sec=2.0)
        assert res["status"] == "success"
        assert res["verdict"]["passed"] is True


@pytest.mark.asyncio
async def test_invoke_resilient_compliance_check_connection_crashed_retry(mock_tool_context):
    # Proves 503 Crashed Server retry behavior
    # Mock failure on first attempt, then success on second
    attempt_count = 0
    
    async def mock_compliance_behavior(context):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise ConnectionError("503 Server Crashed.")
        return {
            "status": "success",
            "verdict": {"passed": True, "violations": []}
        }
        
    with patch("app.fallback_handler.invoke_a2a_compliance_check", side_effect=mock_compliance_behavior):
        res = await invoke_resilient_compliance_check(mock_tool_context, timeout_sec=5.0, max_retries=3, backoff_factor=0.1)
        assert res["status"] == "success"
        assert attempt_count == 2  # Should retry once and then succeed!


@pytest.mark.asyncio
async def test_invoke_resilient_compliance_check_timeout_fallback(mock_tool_context):
    # Proves 30s Timeout Recovery Transition (enforces fail-close to MANUAL_REVIEW)
    # Mock connection lag (sleeps beyond timeout boundaries limit)
    async def mock_lagging_behavior(context):
        await asyncio.sleep(5.0)  # Sleeps 5 seconds
        return {"status": "success"}
        
    with patch("app.fallback_handler.invoke_a2a_compliance_check", side_effect=mock_lagging_behavior):
        # Set target timeout barrier to 1.0 second
        res = await invoke_resilient_compliance_check(mock_tool_context, timeout_sec=1.0, max_retries=1)
        
        # Verify safety transitions
        assert res["status"] == "fallback_manual_review"
        
        state = mock_tool_context.state
        assert state["current_step"] == ComplianceStep.MANUAL_REVIEW
        assert state["compliance_verdict"]["passed"] is False
        assert "SYSTEM TIMEOUT" in state["compliance_verdict"]["violations"][0]
        assert "manual_review" in [span["status"] for span in state["trace_logs"]][0]
        
        logger.info("Resilience verification test PASSED successfully.")
