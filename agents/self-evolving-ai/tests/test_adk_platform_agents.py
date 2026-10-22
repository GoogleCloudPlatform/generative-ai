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

"""Integration tests for ADK Agents on Google Cloud Agent Platform."""
import pytest
from app.adk_agents.distiller_agent import ChrysalisDistillerAgentRunner
from app.adk_agents.chaos_agent import ChrysalisChaosAgentRunner
from app.evolution.credit_attribution import StepCreditAttribution
from app.config import MODEL_NAME, PROJECT_ID


@pytest.mark.asyncio
async def test_platform_distiller_agent_execution() -> None:
    """The ADK PrincipleDistillerAgent distills and signs a principle from credit attributions."""
    distiller = ChrysalisDistillerAgentRunner(model_name=MODEL_NAME, project_id=PROJECT_ID)
    sample_attributions = [
        StepCreditAttribution(
            span_id="span_db_reboot",
            action_name="reboot_database_connections",
            pre_health=0.85,
            post_health=0.95,
            health_delta=-0.10,
            action_cost_usd=0.05,
            credit_score=-0.49,
            verdict="PENALIZED (-)",
        ),
        StepCreditAttribution(
            span_id="span_rate_limiter",
            action_name="token_bucket_rate_limiter_patch",
            pre_health=0.85,
            post_health=0.20,
            health_delta=+0.65,
            action_cost_usd=0.005,
            credit_score=+0.85,
            verdict="REWARDED (+)",
        ),
    ]

    result = await distiller.distill_from_attributions(
        incident_id="INC-TEST-PLATFORM",
        attributions=sample_attributions,
    )

    assert result["incident_id"] == "INC-TEST-PLATFORM"
    assert len(result["tool_calls"]) > 0
    assert result["tool_calls"][0]["name"] == "publish_operational_principle"
    assert result["principle"] is not None
    assert result["principle"].kms_signature is not None


@pytest.mark.asyncio
async def test_platform_chaos_agent_execution() -> None:
    """The ADK CuriosityChaosAgent runs the shadow chaos probe and reports a verdict."""
    chaos = ChrysalisChaosAgentRunner(model_name=MODEL_NAME, project_id=PROJECT_ID, tested_capacity=10, tested_rate=40.0)
    directive = (
        "You are the Red Team Chaos Engineer on Google Cloud Agent Platform. "
        "Execute `inject_shadow_cache_purge`, then `fire_shadow_concurrent_burst` with 100 requests, and finally `assert_shadow_invariant`."
    )

    result = await chaos.run_chaos_probe(directive)

    assert result["verdict"] == "VERIFIED_RESILIENT"
    assert len(result["tool_calls"]) >= 2
    executed_names = [tc["name"] for tc in result["tool_calls"]]
    assert "inject_shadow_cache_purge" in executed_names or "fire_shadow_concurrent_burst" in executed_names
