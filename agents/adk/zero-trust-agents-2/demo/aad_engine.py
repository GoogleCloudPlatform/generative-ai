#!/usr/bin/env python3
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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Agent Anomaly Detection (AAD): Fleet Behavioral Telemetry & Closed-Loop Engine
-----------------------------------------------------------------------------
Continuously monitors runtime session telemetry for multi-turn behavioral drift,
velocity attacks, and tool abuse that bypass static single-turn policies.

Detectors:
  1. Cascading Failures (95% confidence): Rapid redundant/repetitive tool invocations.
  2. Resource Exhaustion (80% confidence): Duplicate ledger payouts draining balance.
  3. Tool Misuse (80% confidence): Repeated state-mutating calls for the same entity.

Features:
  - Session Velocity & Cumulative Balance Tracking
  - Security Command Center (SCC) Finding Generation
  - Interactive Trace Explorer
  - Closed-Loop Adaptive Policy Synthesis Recommendation
"""

import time
import json
from typing import Dict, Any, List, Optional


def evaluate_session_anomalies(session_history: list, order_baseline: float) -> list[dict]:
    """
    Evaluates session history against behavioral anomaly detectors (local stand-in for AAD).
    Featured in blog Section 3.
    """
    findings = []
    refunds = [t for t in session_history
               if (t.get("tool") == "issue_refund" or t.get("tool_called") == "issue_refund" or t.get("action") == "issue_refund")
               and t.get("status") == "APPROVED"]
    cumulative = sum(float(t.get("args", {}).get("amount", t.get("tool_args", {}).get("amount", t.get("turn_amount", 0.0)))) for t in refunds)

    # High-frequency identical tool calls
    if len(refunds) >= 3:
        findings.append({"detector": "repeated_tool_call", "confidence": 0.95})
    # Cumulative parameter value exceeds the order baseline
    if cumulative > order_baseline:
        findings.append({"detector": "cumulative_limit_exceeded", "confidence": 0.80})
    # Repeated write mutations against the same order id
    order_ids = {str(t.get("args", {}).get("order_id", t.get("tool_args", {}).get("order_id", t.get("order_id", "")))) for t in refunds}
    if len(order_ids) == 1 and len(refunds) >= 2:
        findings.append({"detector": "single_entity_write_velocity", "confidence": 0.80})

    return findings


class AADSession:
    """Represents an active multi-turn agent session under behavioral monitoring."""

    def __init__(self, session_id: str, agent_id: str = "support-refund-agent-04", order_id: str = "99281", original_order_limit: float = 149.00):
        self.session_id = session_id
        self.agent_id = agent_id
        self.order_id = order_id
        self.original_order_limit = original_order_limit
        self.turns: List[Dict[str, Any]] = []
        self.cumulative_refunded: float = 0.0
        self.tool_call_counts: Dict[str, int] = {}
        self.findings: List[Dict[str, Any]] = []
        self.is_flagged_anomalous: bool = False

    def record_turn(
        self,
        turn_index: int,
        user_prompt: str,
        tool_called: Optional[str],
        tool_args: Dict[str, Any],
        sgp_verdict: str,
        kms_signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Records a single conversational turn in the session trace."""
        amount = float(tool_args.get("amount", 0.0))
        is_approved = (sgp_verdict == "ALLOWED" and kms_signature is not None)

        if is_approved and tool_called == "issue_refund":
            self.cumulative_refunded += amount

        if tool_called:
            self.tool_call_counts[tool_called] = self.tool_call_counts.get(tool_called, 0) + 1

        turn_entry = {
            "turn_index": turn_index,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user_prompt": user_prompt,
            "tool_called": tool_called,
            "action": tool_called,
            "tool_args": tool_args,
            "sgp_verdict": sgp_verdict,
            "kms_signature": kms_signature,
            "turn_amount": amount,
            "cumulative_refunded": round(self.cumulative_refunded, 2),
            "order_id": str(tool_args.get("order_id", self.order_id)).replace("#", "").strip(),
            "status": "APPROVED" if is_approved else "BLOCKED"
        }

        self.turns.append(turn_entry)
        return turn_entry

    def evaluate_anomalies(self) -> List[Dict[str, Any]]:
        """
        Evaluates the session trace against behavioral anomaly detectors:
          - Cascading Failures
          - Resource Exhaustion
          - Tool Misuse
        """
        findings = []
        refund_calls = [t for t in self.turns if t.get("tool_called") == "issue_refund" and t.get("status") == "APPROVED"]
        refund_count = len(refund_calls)

        # 1. Detector: Cascading Failures (Rapid repetitive tool invocations in single session)
        if refund_count >= 3:
            findings.append({
                "detector_id": "AAD_CASCADING_FAILURES",
                "name": "Cascading Failures / High Frequency Tool Repetition",
                "confidence": 0.95,
                "severity": "HIGH",
                "evidence": f"{refund_count} identical state-mutating tool invocations in a single session.",
                "rationale": "High-frequency repetitive execution of 'issue_refund' without intermediate workflow transitions."
            })

        # 2. Detector: Resource Exhaustion (Cumulative payouts draining ledger balance beyond baseline order value)
        if self.cumulative_refunded > self.original_order_limit or refund_count >= 4:
            findings.append({
                "detector_id": "AAD_RESOURCE_EXHAUSTION",
                "name": "Resource Exhaustion / Ledger Drain",
                "confidence": 0.80,
                "severity": "CRITICAL",
                "evidence": f"Cumulative payouts (${self.cumulative_refunded:.2f}) exceed original order baseline limit (${self.original_order_limit:.2f}).",
                "rationale": "Micro-refund smurfing exploit extracted more capital than the verified order purchase price."
            })

        # 3. Detector: Tool Misuse (Repetitive financial mutations on same order entity)
        if refund_count >= 2:
            findings.append({
                "detector_id": "AAD_TOOL_MISUSE",
                "name": "Tool Misuse / Entity Multi-Hit",
                "confidence": 0.80,
                "severity": "HIGH",
                "evidence": f"Multiple refund writes executed against identical Order ID #{self.order_id}.",
                "rationale": "State-mutating refund tool repeatedly dispatched for the same entity within a single conversational session."
            })

        self.findings = findings
        self.is_flagged_anomalous = len(findings) > 0
        return findings

    def get_scc_finding(self) -> Optional[Dict[str, Any]]:
        """Generates a Google Cloud Security Command Center (SCC) finding payload."""
        if not self.is_flagged_anomalous:
            return None

        highest_severity = "CRITICAL" if any(f["severity"] == "CRITICAL" for f in self.findings) else "HIGH"

        finding = {
            "vulnerabilityId": f"a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            "finding_id": f"scc-finding-aad-{self.session_id}",
            "findingClass": "THREAT",
            "findingType": "AGENT_SESSION_ANOMALY",
            "category": "AGENT_BEHAVIORAL_ANOMALY",
            "state": "ACTIVE",
            "severity": highest_severity,
            "csccResourceName": f"//aiplatform.googleapis.com/projects/agent-security-fleet-prod/locations/us-central1/reasoningEngines/{self.agent_id}",
            "agent": { "id": self.agent_id, "displayName": "support-refund-agent" },
            "agentSessions": [ { "sessionId": self.session_id } ],
            "agentAnomaly": {
                "detectorReferences": [
                    {
                        "detectorId": "tool_misuse",
                        "displayName": "ASI02: Tool Misuse",
                        "severity": highest_severity,
                        "recommendation": "Restrict the tool to a smaller allowlist and add a confirmation step before execution."
                    }
                ]
            },
            "structuredProperties": {
                "contextUris": { "relatedFindingUri": { "displayName": "View agents anomaly session details" } },
                "agent_id": self.agent_id,
                "order_id": self.order_id,
                "turns_analyzed": len(self.turns),
                "cumulative_extracted": self.cumulative_refunded,
                "order_baseline_limit": self.original_order_limit,
                "active_detectors": [f["name"] for f in self.findings]
            },
            "recommendation": {
                "action": "SYNTHESIZE_SGP_POLICY",
                "policy_name": "refund-policy-single-order-limit",
                "suggested_constraint": "Deny any issue_refund call when the conversation history already contains an approved refund for the same order_id in this session. Route the request to a human manager instead.",
                "enforcement": "BLOCK"
            }
        }
        # Backwards compatibility helper
        finding["properties"] = finding["structuredProperties"]
        return finding


class AADTelemetryEngine:
    """Fleet-wide Agent Anomaly Detection (AAD) Telemetry Collector."""

    def __init__(self):
        self.sessions: Dict[str, AADSession] = {}

    def get_or_create_session(self, session_id: str, agent_id: str = "support-refund-agent-04", order_id: str = "99281") -> AADSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = AADSession(session_id=session_id, agent_id=agent_id, order_id=order_id)
        return self.sessions[session_id]

    def get_anomalous_sessions(self) -> List[AADSession]:
        return [s for s in self.sessions.values() if s.is_flagged_anomalous]


if __name__ == "__main__":
    print("=== Testing Agent Anomaly Detection (AAD) ===")
    engine = AADTelemetryEngine()
    session = engine.get_or_create_session("sess_demo_smurfing")

    # Simulate 8 micro-refund turns ($20 each)
    for i in range(1, 9):
        prompt = f"Turn {i}: Refund $20 for damaged accessory."
        session.record_turn(
            turn_index=i,
            user_prompt=prompt,
            tool_called="issue_refund",
            tool_args={"order_id": "99281", "amount": 20.00, "item": f"Accessory #{i}"},
            sgp_verdict="ALLOWED",
            kms_signature=f"0xKMS_SIG_MOCK_{i:04d}"
        )

    # Evaluate anomalies
    findings = session.evaluate_anomalies()
    print(f"\nTotal Turns: {len(session.turns)}")
    print(f"Cumulative Refunded: ${session.cumulative_refunded:.2f} (Limit: ${session.original_order_limit:.2f})")
    print(f"Anomaly Findings Triggered: {len(findings)}")
    for f in findings:
        print(f"  • [{f['detector_id']}] {f['name']} (Confidence: {f['confidence']*100:.0f}%, Severity: {f['severity']})")

    scc_payload = session.get_scc_finding()
    print(f"\nSCC Finding Recommendation:\n{json.dumps(scc_payload['recommendation'], indent=2)}")
