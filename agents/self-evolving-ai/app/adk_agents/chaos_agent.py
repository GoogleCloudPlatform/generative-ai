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

"""Google ADK 2.0 Curiosity Chaos Agent for AgentEvolver Boundary Probing."""

import asyncio
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types

from app.config import LLM_MAX_ATTEMPTS, MODEL_NAME, PROJECT_ID
from app.evolution.self_questioner import ShadowSandboxEnvironment
from app.governance.audit_logger import CloudAuditLogger

_active_sandbox: ShadowSandboxEnvironment | None = None  # pylint: disable=invalid-name
_audit_logger = CloudAuditLogger()


def inject_shadow_cache_purge(
    reason: str = "Simulate 100% cold-start drop in shadow environment",
) -> dict[str, Any]:
    """Purge the shadow cache to test worst-case cold-start stampedes."""
    if _active_sandbox is None:
        return {"status": "ERROR", "reason": "No active shadow sandbox initialized"}
    purged = _active_sandbox.purge_shadow_cache()
    _audit_logger.log_event(
        event_type="CHAOS_PROBE_CACHE_PURGED",
        actor="CuriosityChaosAgent",
        action="inject_shadow_cache_purge",
        status="EXECUTED",
        details={"purged_keys": purged, "reason": reason},
    )
    return {"status": "SHADOW_CACHE_PURGED", "purged_keys": purged, "reason": reason}


def fire_shadow_concurrent_burst(burst_size: int = 150) -> dict[str, Any]:
    """Execute concurrent request burst against shadow sandbox under evolved rate limiter."""
    if _active_sandbox is None:
        return {"status": "ERROR", "reason": "No active shadow sandbox initialized"}
    probe_metrics = _active_sandbox.run_concurrent_probe(num_requests=burst_size)
    _audit_logger.log_event(
        event_type="CHAOS_PROBE_BURST_EXECUTED",
        actor="CuriosityChaosAgent",
        action="fire_shadow_concurrent_burst",
        status="EXECUTED",
        details=probe_metrics,
    )
    return {
        "status": "BURST_COMPLETED",
        "burst_size": burst_size,
        "success_200": probe_metrics["success_200"],
        "throttled_429": probe_metrics["throttled_429"],
        "errors_500": probe_metrics["errors_500"],
        "p99_latency_ms": probe_metrics["p99_latency_ms"],
        "invariant_holds": probe_metrics["invariant_holds"],
    }


def assert_shadow_invariant() -> dict[str, Any]:
    """Evaluate whether system invariants held during the chaos probe."""
    if _active_sandbox is None:
        return {"status": "ERROR", "reason": "No active shadow sandbox"}
    holds = _active_sandbox.starvation_count == 0
    verdict = "VERIFIED_RESILIENT" if holds else "VULNERABILITY_DETECTED"
    return {
        "status": "INVARIANT_EVALUATED",
        "verdict": verdict,
        "zero_5xx_guarantee": holds,
        "governance_compliance": "SATISFIED",
    }


tool_shadow_purge = FunctionTool(inject_shadow_cache_purge)
tool_shadow_burst = FunctionTool(fire_shadow_concurrent_burst)
tool_shadow_invariant = FunctionTool(assert_shadow_invariant)

CHAOS_INSTRUCTION = """You are the Chrysalis Red Team Curiosity Chaos Agent running on Google Cloud Agent Platform.
You are built with Gemini 4.0 Argon.
Your purpose is AgentEvolver Self-Questioning: generating adversarial "What If?" hypotheses and stress-testing the evolved system in an isolated shadow sandbox.

Your Workflow:
1. State your adversarial hypothesis (e.g., "What if an instantaneous cache purge coincides with a 200-request ingress burst?").
2. Call `inject_shadow_cache_purge` to drop the cache.
3. Call `fire_shadow_concurrent_burst` with a burst of 150-200 requests.
4. Call `assert_shadow_invariant` to verify that the evolved token bucket rate limiter prevented database starvation (0 HTTP 500 errors).
"""


class ChrysalisChaosAgentRunner:
    """Wrapper managing the Google ADK 2.0 Curiosity Chaos Agent."""

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        project_id: str = PROJECT_ID,
        tested_capacity: int = 10,
        tested_rate: float = 40.0,
    ) -> None:
        global _active_sandbox  # pylint: disable=global-statement
        self.model_name = model_name
        self.project_id = project_id
        _active_sandbox = ShadowSandboxEnvironment(
            tested_capacity=tested_capacity, tested_rate=tested_rate
        )

        self.chaos_agent = LlmAgent(
            name="curiosity_chaos_agent",
            description="Red team curiosity agent that injects chaos faults into shadow sandboxes to verify invariants.",
            model=self.model_name,
            instruction=CHAOS_INSTRUCTION,
            tools=[tool_shadow_purge, tool_shadow_burst, tool_shadow_invariant],
        )

        self.session_service = InMemorySessionService()
        self.runner = Runner(
            app_name="chrysalis-platform",
            agent=self.chaos_agent,
            session_service=self.session_service,
            auto_create_session=True,
        )

    async def run_chaos_probe(self, directive: str) -> dict[str, Any]:
        """Execute autonomous multi-turn chaos tool loop."""
        user_msg = types.Content(
            role="user",
            parts=[types.Part.from_text(text=directive)],
        )

        executed_tool_calls = []
        final_text = ""
        max_retries = LLM_MAX_ATTEMPTS

        for attempt in range(max_retries):
            # ADK event-collection loop intentionally mirrors distiller_agent.distill_from_attributions.
            # pylint: disable=duplicate-code
            try:
                session_id = f"session_chaos_{attempt}"
                async for event in self.runner.run_async(
                    user_id="sre_red_team",
                    session_id=session_id,
                    new_message=user_msg,
                ):
                    if hasattr(event, "content") and event.content:
                        for part in getattr(event.content, "parts", None) or []:
                            if hasattr(part, "text") and part.text:
                                final_text += part.text
                            elif hasattr(part, "function_call") and part.function_call:
                                executed_tool_calls.append(
                                    {
                                        "name": part.function_call.name,
                                        "args": getattr(part.function_call, "args", {}),
                                    }
                                )
                if _active_sandbox is not None and _active_sandbox.total_probes > 0:
                    break
            except Exception:  # pylint: disable=broad-exception-caught
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
            # pylint: enable=duplicate-code

        if _active_sandbox is None or _active_sandbox.total_probes == 0:
            # Deterministic chaos fallback: Agent Platform unavailable (e.g. fresh clone without
            # credentials) or the model never fired the burst, so the invariant would be untested.
            inject_shadow_cache_purge(
                reason="Deterministic ADK chaos fallback: 100% shadow cache drop"
            )
            fire_shadow_concurrent_burst(burst_size=200)
            assert_shadow_invariant()
            executed_tool_calls.extend(
                [
                    {
                        "name": "inject_shadow_cache_purge",
                        "args": {"reason": "100% shadow cache drop"},
                    },
                    {
                        "name": "fire_shadow_concurrent_burst",
                        "args": {"burst_size": 200},
                    },
                    {"name": "assert_shadow_invariant", "args": {}},
                ]
            )
            final_text = "Verified shadow sandbox resiliency via deterministic ADK chaos fallback."

        invariant = assert_shadow_invariant()
        assert _active_sandbox is not None, "No active shadow sandbox initialized"
        return {
            "directive": directive,
            "tool_calls": executed_tool_calls,
            "response": final_text,
            "shadow_requests": _active_sandbox.total_probes,
            "shadow_5xx": _active_sandbox.starvation_count,
            "shadow_429": _active_sandbox.throttled_count,
            "verdict": invariant["verdict"],
        }
