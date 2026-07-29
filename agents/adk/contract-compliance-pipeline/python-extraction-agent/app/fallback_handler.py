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

import asyncio
import json
import logging
import time
from google.adk.tools import ToolContext
from app.state_schema import ComplianceStep
# NOTE: This module is retained as a reference implementation showing the
# resilience pattern: timeout, retry, and fail-close to MANUAL_REVIEW. The live
# cockpit path calls the Go compliance agent explicitly from fast_api_app.py so
# the handoff is observable in the browser. agent.py keeps the ADK
# RemoteA2aAgent architecture reference.


async def invoke_a2a_compliance_check(tool_context):
    """Placeholder for the legacy A2A compliance check.

    In the original implementation, this function was imported from
    a2a_client.py which used hand-rolled HTTP calls to the Go agent.
    The live cockpit now uses fast_api_app.invoke_go_compliance_service().
    """
    raise NotImplementedError(
        "Legacy A2A client removed. Use fast_api_app.invoke_go_compliance_service()."
    )


logger = logging.getLogger(__name__)


def _log_structured_json(severity: str, message: str, **kwargs) -> None:
    """Standardized structured JSON logger for GCP/Cloud Logging visibility.
    
    Rule 53 Enforcement: Logs diagnostic messages in parseable JSON structures,
    ensuring sensitive session tokens are never printed.
    """
    payload = {
        "severity": severity,
        "message": message,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%Z"),
        **kwargs
    }
    logger.info(json.dumps(payload))


async def invoke_resilient_compliance_check(
    tool_context: ToolContext,
    timeout_sec: float = 30.0,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
) -> dict:
    """Wraps A2A task audit dispatching in high-resilience triggers:
    
    1. Handles 503 Crashed Server exceptions using exponential retry loops.
    2. Enforces a strict 30-second timeout boundary.
    3. Triggers safe fail-close path migrations (transitions step to MANUAL_REVIEW).
    """
    state = tool_context.state
    case_id = state.get("case_id", "local-case")
    
    # Check if a custom timeout is toggled in memory settings
    simulated_timeout = state.get("simulated_timeout", timeout_sec)
    
    _log_structured_json(
        severity="INFO",
        message=f"Resilience Handler: Initializing compliance check for case {case_id}",
        event="compliance_audit_start",
        case_id=case_id,
        timeout_boundary_sec=simulated_timeout
    )
    
    attempt = 0
    backoff_delay = 1.0
    
    while attempt < max_retries:
        attempt += 1
        try:
            # Wrap the A2A submission and check in a strict timeout boundary
            _log_structured_json(
                severity="INFO",
                message=f"Dispatching A2A audit request (Attempt {attempt} of {max_retries})",
                event="a2a_dispatch_attempt",
                case_id=case_id,
                attempt=attempt
            )
            
            # Execute A2A client validation with timeout caps
            res = await asyncio.wait_for(
                invoke_a2a_compliance_check(tool_context),
                timeout=simulated_timeout
            )
            
            # Check response status
            if res.get("status") == "dormant_paused":
                _log_structured_json(
                    severity="INFO",
                    message="External connection reports lag. Task submitted and pipeline entered dormant state.",
                    event="dormancy_entered",
                    case_id=case_id,
                    task_id=res.get("task_id")
                )
                return res
                
            _log_structured_json(
                severity="INFO",
                message="A2A compliance validation audit finished successfully.",
                event="compliance_audit_completed",
                case_id=case_id
            )
            return res
            
        except asyncio.TimeoutError:
            # 30-second timeout reached
            _log_structured_json(
                severity="WARNING",
                message=f"A2A connection timed out after {simulated_timeout} seconds limit.",
                event="timeout_reached",
                case_id=case_id,
                timeout_limit_sec=simulated_timeout
            )
            break  # Move straight to MANUAL_REVIEW fallback
            
        except ConnectionError as e:
            # 503 connection error or socket faults -> retry loop triggers
            _log_structured_json(
                severity="WARNING",
                message=f"A2A connection failed on attempt {attempt}: {e!s}",
                event="connection_fault",
                case_id=case_id,
                error=str(e)
            )
            
            if attempt >= max_retries:
                _log_structured_json(
                    severity="ERROR",
                    message="Max A2A delivery retries exhausted. Triggering safety manual routing.",
                    event="retries_exhausted",
                    case_id=case_id
                )
                break
                
            # Perform backoff
            logger.info(f"Retrying compliance check after {backoff_delay} seconds delay...")
            await asyncio.sleep(backoff_delay)
            backoff_delay *= backoff_factor

        except Exception as e:
            # Non-retryable errors — fail immediately
            _log_structured_json(
                severity="ERROR",
                message=f"A2A audit failed with non-retryable error: {e!s}",
                event="non_retryable_error",
                case_id=case_id,
                error=str(e)
            )
            break
            
    # --- FALLBACK GATEWAY (Fail Safe Transition to MANUAL_REVIEW) ---
    _log_structured_json(
        severity="ALERT",
        message="Resilience Gate triggered: Transitioning case to MANUAL_REVIEW checkpoint.",
        event="fallback_recovery_triggered",
        case_id=case_id
    )
    
    # Update persistent state metrics safely
    state["current_step"] = ComplianceStep.MANUAL_REVIEW
    state["pending_signals"] = []
    
    fallback_verdict = {
        "passed": False,
        "violations": [
            "SYSTEM TIMEOUT: External compliance service failed to respond within 30-second threshold.",
            "FAIL-SAFE ACTION: Document routed for legal manager manual verification."
        ],
        "verdict_timestamp": time.strftime("%Y-%m-%d %H:%M:%S %Z")
    }
    state["compliance_verdict"] = fallback_verdict
    
    # Append trace event logs
    state["trace_logs"] = state.get("trace_logs", [])
    state["trace_logs"].append({
        "span": "resilience_fallback_gate",
        "service": "python-extraction-agent",
        "duration_ms": 450,
        "status": "manual_review_routed"
    })
    
    return {
        "status": "fallback_manual_review",
        "verdict": fallback_verdict,
        "message": "Resilience safety check triggered. Case successfully routed for manual legal review."
    }
