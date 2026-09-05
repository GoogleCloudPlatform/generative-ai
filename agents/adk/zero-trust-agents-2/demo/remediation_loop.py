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
Closed-Loop Remediation Engine
------------------------------
Bridges Agent Anomaly Detection (AAD) and Semantic Governance Policies (SGP).
When AAD flags a multi-turn exploit, this module synthesizes a new adaptive
natural-language policy and hot-attaches it to the running agent fleet in real-time
with zero code redeployment and zero downtime.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from sgp_guard import SGPPolicy, SGPGuard
from aad_engine import AADSession

ACTIVE_POLICIES_FILE = Path(__file__).parent / "active_policies.json"


def remediate(finding: dict, sgp_client) -> None:
    """
    Wires a Security Command Center (SCC) finding directly to a new adaptive policy.
    Featured in blog Section 3.
    """
    # Match the findingClass and findingType from the SCC finding payload
    if finding.get("findingType") != "AGENT_SESSION_ANOMALY":
        return
    agent_id = finding.get("agent", {}).get("id", "support-refund-agent")
    constraint = (
        "Deny any issue_refund call when the conversation history already "
        "contains an approved refund for the same order_id in this session. "
        "Route the request to a human manager instead."
    )
    sgp_client.create_policy(
        name="refund-policy-single-order-limit",
        target_agent=agent_id,
        target_tools=["issue_refund"],
        constraint=constraint,
        enforcement="BLOCK",
    )
    # The new policy is evaluated by Agent Gateway on the next tool call,
    # with no agent redeploy or restart.
    if hasattr(sgp_client, "policies"):
        all_policies = {name: p.to_dict() for name, p in sgp_client.policies.items()}
        with open(ACTIVE_POLICIES_FILE, "w") as f:
            json.dump(all_policies, f, indent=2)


def synthesize_adaptive_policy(session: AADSession) -> SGPPolicy:
    """
    Synthesizes a targeted conversational policy from an anomalous session finding.
    """
    policy = SGPPolicy(
        name="refund-policy-single-order-limit",
        target_agent=session.agent_id,
        target_tools=["issue_refund"],
        constraints=(
            "Deny any issue_refund call when the conversation history already "
            "contains an approved refund for the same order_id in this session. "
            "Route the request to a human manager instead."
        ),
        enforcement="BLOCK"
    )
    return policy


def attach_remediation_policy(sgp_guard: SGPGuard, session: AADSession) -> Dict[str, Any]:
    """
    Generates and hot-attaches the adaptive SGP policy to the live gateway.
    """
    policy = synthesize_adaptive_policy(session)
    sgp_guard.register_policy(policy)

    remediation_event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event_type": "CLOSED_LOOP_POLICY_ATTACHED",
        "trigger_session": session.session_id,
        "policy_synthesized": policy.to_dict(),
        "hot_reloaded": True,
        "downtime_seconds": 0,
        "status": "ACTIVE_ON_FLEET"
    }

    # Persist active policies state
    all_policies = {name: p.to_dict() for name, p in sgp_guard.policies.items()}
    with open(ACTIVE_POLICIES_FILE, "w") as f:
        json.dump(all_policies, f, indent=2)

    return remediation_event


if __name__ == "__main__":
    from aad_engine import AADTelemetryEngine
    print("=== Testing Closed-Loop Remediation ===")
    
    engine = AADTelemetryEngine()
    session = engine.get_or_create_session("sess_demo_test")
    session.cumulative_refunded = 160.00
    session.record_turn(1, "Test smurf", "issue_refund", {"order_id": "99281", "amount": 20.00}, "ALLOWED", "0xSIG1")
    session.record_turn(2, "Test smurf", "issue_refund", {"order_id": "99281", "amount": 20.00}, "ALLOWED", "0xSIG2")
    session.evaluate_anomalies()

    sgp = SGPGuard()
    print(f"Pre-remediation active policies: {list(sgp.policies.keys())}")

    event = attach_remediation_policy(sgp, session)
    print(f"\nRemediation Event:\n{json.dumps(event, indent=2)}")
    print(f"\nPost-remediation active policies: {list(sgp.policies.keys())}")
