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

"""Google ADK 2.0 Principle Distiller Agent with Cloud KMS Signing."""
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types

from app.config import MODEL_NAME, PROJECT_ID, LLM_MAX_ATTEMPTS
from app.evolution.cloud_principle_store import CloudPrincipleStore, PrincipleRecord
from app.evolution.credit_attribution import StepCreditAttribution
from app.governance.audit_logger import CloudAuditLogger

# Self-Navigating memory is shared with the diagnostic agent (see tools_library.get_principle_store).
_audit_logger = CloudAuditLogger()

DISTILLER_INSTRUCTION = """You are the Chrysalis Principle Distillation Specialist Agent running on Google Cloud Agent Platform.
You are built with Gemini 4.0 Argon.
Your purpose is APEX Layer 2: extracting durable, generalized invariant rules from SRE incident remediation trajectories and persisting them signed with Cloud KMS into Agent Platform vector memory.

Your Responsibilities:
1. Ingest fine-grained StepCreditAttribution data from AgentEvolver.
2. Identify actions penalized with negative credit (e.g. database reboots during cache stampedes) -> label them CONTRAINDICATED.
3. Identify actions rewarded with positive credit (e.g. token bucket rate limiting) -> label them RECOMMENDED.
4. Synthesize a generalized trigger pattern describing the failure mode.
5. Call `publish_operational_principle` with your distilled rule.
"""


def _get_default_store() -> CloudPrincipleStore:
    # Shared Self-Navigating memory: the same store the diagnostic agent queries.
    from app.adk_agents.tools_library import get_principle_store  # pylint: disable=import-outside-toplevel

    return get_principle_store()


class ChrysalisDistillerAgentRunner:  # pylint: disable=too-many-instance-attributes
    """Wrapper managing the Google ADK 2.0 Principle Distiller Agent."""

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        project_id: str = PROJECT_ID,
        principle_store: Optional[CloudPrincipleStore] = None,
    ):
        self.model_name = model_name
        self.project_id = project_id
        self.principle_store = principle_store or _get_default_store()
        self.published: List[PrincipleRecord] = []

        def publish_operational_principle(
            trigger_pattern: str,
            contraindicated_actions: List[str],
            recommended_actions: List[str],
            confidence_score: float = 0.95,
            incident_id: str = "INC-PLATFORM-001",
        ) -> Dict[str, Any]:
            """Publish a newly distilled operational principle signed with Cloud KMS into Agent Platform vector memory."""
            record = self.principle_store.add_principle(
                trigger_pattern=trigger_pattern,
                contraindicated=contraindicated_actions,
                recommended=recommended_actions,
                confidence=confidence_score,
                incident_id=incident_id,
            )
            self.published.append(record)
            _audit_logger.log_event(
                event_type="PRINCIPLE_DISTILLED_KMS_SIGNED",
                actor="PrincipleDistillerAgent",
                action="publish_operational_principle",
                status="SUCCESS",
                details={
                    "principle_id": record.principle_id,
                    "kms_key": record.kms_signature.key_resource_name if record.kms_signature else None,
                    "contraindicated": contraindicated_actions,
                    "recommended": recommended_actions,
                },
            )
            return {
                "status": "PUBLISHED_AND_SIGNED",
                "principle_id": record.principle_id,
                "trigger_pattern": record.trigger_pattern,
                "contraindicated": record.contraindicated_actions,
                "recommended": record.recommended_actions,
                "confidence_score": record.confidence_score,
                "kms_signature": record.kms_signature.signature_base64 if record.kms_signature else None,
            }

        self._publish = publish_operational_principle
        self.distiller_agent = LlmAgent(
            name="principle_distiller_agent",
            description="Specialist agent that extracts generalized operational invariants and signs them with Cloud KMS.",
            model=self.model_name,
            instruction=DISTILLER_INSTRUCTION,
            tools=[FunctionTool(publish_operational_principle)],
        )
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            app_name="chrysalis-platform",
            agent=self.distiller_agent,
            session_service=self.session_service,
            auto_create_session=True,
        )

    async def distill_from_attributions(  # pylint: disable=too-many-locals
        self,
        incident_id: str,
        attributions: List[StepCreditAttribution],
    ) -> Dict[str, Any]:
        """Run PrincipleDistillerAgent to extract and publish a principle."""
        attr_summary = [
            f"Span: {a.span_id} | Action: {a.action_name} | Credit: {a.credit_score:+.2f} | Verdict: {a.verdict}"
            for a in attributions
        ]
        prompt = (
            f"Incident ID: {incident_id}\n"
            f"AgentEvolver Step Credit Attributions:\n" + "\n".join(attr_summary) + "\n\n"
            "Analyze these results and call `publish_operational_principle` with the distilled rule."
        )

        user_msg = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )

        executed_tool_calls = []
        final_text = ""
        max_retries = LLM_MAX_ATTEMPTS
        published_before = len(self.published)
        source = "gemini"

        for attempt in range(max_retries):
            try:
                session_id = f"session_distill_{uuid.uuid4().hex[:8]}_{attempt}"
                async for event in self.runner.run_async(
                    user_id="sre_operator",
                    session_id=session_id,
                    new_message=user_msg,
                ):
                    if hasattr(event, "content") and event.content:
                        for part in getattr(event.content, "parts", None) or []:
                            if hasattr(part, "text") and part.text:
                                final_text += part.text
                            elif hasattr(part, "function_call") and part.function_call:
                                executed_tool_calls.append({
                                    "name": part.function_call.name,
                                    "args": dict(getattr(part.function_call, "args", None) or {}),
                                })
                if len(self.published) > published_before:
                    break
            except Exception:  # pylint: disable=broad-exception-caught
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))

        if len(self.published) == published_before:
            # Deterministic tool fallback: Agent Platform unavailable (e.g. fresh clone without
            # credentials) or the model answered without calling the publish tool.
            source = "deterministic_fallback"
            contraindicated = [a.action_name for a in attributions if a.credit_score < 0] or ["reboot_database_connections"]
            recommended = [a.action_name for a in attributions if a.credit_score > 0] or ["token_bucket_rate_limiter_patch"]
            await asyncio.to_thread(
                self._publish,
                trigger_pattern="Cache eviction stampede causing database connection pool saturation under high ingress",
                contraindicated_actions=contraindicated,
                recommended_actions=recommended,
                confidence_score=0.98,
                incident_id=incident_id,
            )
            executed_tool_calls.append({
                "name": "publish_operational_principle",
                "args": {"incident_id": incident_id, "contraindicated_actions": contraindicated, "recommended_actions": recommended},
            })
            final_text = "Distilled operational principle via deterministic ADK tool fallback."

        return {
            "incident_id": incident_id,
            "tool_calls": executed_tool_calls,
            "distiller_response": final_text,
            "principle": self.published[-1],
            "source": source,
        }
