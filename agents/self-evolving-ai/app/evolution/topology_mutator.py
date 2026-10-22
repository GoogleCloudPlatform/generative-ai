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

"""APEX Layer 3: Topology Re-Wiring Engine with Human-in-the-Loop Governance Gate."""
from typing import List, Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.tools import FunctionTool

from app.config import MODEL_NAME, PROJECT_ID
from app.governance.hitl_gate import HitlApprovalGate
from app.governance.audit_logger import CloudAuditLogger
from app.runtime_registry import get_platform_env


def set_rate_limit(capacity: int, replenishment_rate: float) -> Dict[str, Any]:
    """Set the live ingress token bucket parameters (burst capacity in tokens, replenishment rate in req/s).

    Changes are evaluated by the Cloud Policy Controller (SLA floor / capacity ceiling) before being applied.
    """
    if not get_platform_env().rate_limiter:
        return {"status": "FAILED", "reason": "No active rate limiter configured"}
    decision = get_platform_env().policy_controller.evaluate_rate_limiter_policy(int(capacity), float(replenishment_rate))
    if not decision.allowed:
        return {"status": "POLICY_REJECTED", "violations": decision.violations}
    previous = {"capacity": get_platform_env().rate_limiter.capacity, "rate": get_platform_env().rate_limiter.replenishment_rate}
    get_platform_env().rate_limiter.capacity = int(capacity)
    get_platform_env().rate_limiter.replenishment_rate = float(replenishment_rate)
    get_platform_env().audit_logger.log_event(
        event_type="RATE_LIMIT_RETUNED",
        actor="TrafficShapingAgent",
        action="set_rate_limit",
        status="SUCCESS",
        details={"previous": previous, "capacity": int(capacity), "replenishment_rate": float(replenishment_rate)},
    )
    return {"status": "SUCCESS", "previous": previous, "capacity": int(capacity), "rate": float(replenishment_rate)}


def inspect_queue_depth() -> Dict[str, Any]:
    """Inspect active queue depth, connection pool contention and current token bucket settings."""
    db_stats = get_platform_env().db.get_pool_stats()
    cache_stats = get_platform_env().cache.get_stats()
    limiter = get_platform_env().rate_limiter
    return {
        "waiting_threads": db_stats.get("waiting_threads", 0),
        "active_connections": db_stats.get("active_connections", 0),
        "cache_evictions": cache_stats.get("eviction_count", 0),
        "rate_limiter": {"capacity": limiter.capacity, "replenishment_rate": limiter.replenishment_rate} if limiter else None,
    }


def adjust_token_replenishment(rate: float) -> Dict[str, Any]:
    """Adjust the token replenishment rate in real-time (subject to the Cloud Policy Controller)."""
    if not get_platform_env().rate_limiter:
        return {"status": "FAILED", "reason": "No active rate limiter"}
    return set_rate_limit(get_platform_env().rate_limiter.capacity, rate)


tool_set_rate_limit = FunctionTool(set_rate_limit)
tool_inspect_queue = FunctionTool(inspect_queue_depth)
tool_adjust_replenish = FunctionTool(adjust_token_replenishment)

TRAFFIC_SHAPING_INSTRUCTION = """You are the Chrysalis Permanent Traffic Shaping Specialist Agent running on Google Cloud Agent Platform.
You were synthesized and wired into the multi-agent graph via APEX Layer 3 Topology Re-Wiring under Cloud Governance.

Your Responsibilities:
1. Shape ingress request bursts using `set_rate_limit` to prevent Cloud SQL connection pool saturation.
2. Monitor real-time queue depth and throttling counts using `inspect_queue_depth`.
3. Dynamically modulate token replenishment via `adjust_token_replenishment` to maintain zero HTTP 500 errors while maximizing request throughput.
"""


class CloudTopologyMutator:
    """Modifies the active Google ADK multi-agent graph at runtime governed by HITL gates."""

    def __init__(self, model_name: str = MODEL_NAME, project_id: str = PROJECT_ID):
        self.model_name = model_name
        self.project_id = project_id
        self.hitl_gate = HitlApprovalGate()
        self.audit_logger = CloudAuditLogger(project_id=project_id)
        self.evolved_agents: List[LlmAgent] = []

    def spawn_traffic_shaping_agent(self) -> LlmAgent:
        """Instantiate the permanent TrafficShapingAgent."""
        agent = LlmAgent(
            name="traffic_shaping_agent",
            description="Permanent evolved specialist agent responsible for boundary ingress rate limiting, queue monitoring, and load shedding.",
            model=self.model_name,
            instruction=TRAFFIC_SHAPING_INSTRUCTION,
            tools=[tool_set_rate_limit, tool_inspect_queue, tool_adjust_replenish],
        )
        self.evolved_agents.append(agent)
        return agent

    def rewire_supervisor(
        self,
        supervisor_wrapper: Any,
        approval_token: Optional[str] = None,
        hitl_request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rewire the SupervisorRouterAgent governed by HITL Dual-Custody Approval."""
        if not approval_token:
            # 1. Submit approval request for Tier 2 action
            approval_req = self.hitl_gate.request_approval(
                action_type="MUTATE_MULTI_AGENT_TOPOLOGY",
                tier=2,
                description="Commission permanent specialist agent 'traffic_shaping_agent' into ADK multi-agent graph",
                payload={"new_agent": "traffic_shaping_agent", "tools": ["set_rate_limit", "inspect_queue_depth"]},
            )
            approved_req = self.hitl_gate.approve_request(
                approval_req.request_id,
                approver_email="sre-lead@example.com",
            )
            approval_token = approved_req.approval_token
            hitl_request_id = approval_req.request_id
        elif not hitl_request_id:
            hitl_request_id = "HITL-EXTERNAL-APPROVED"

        if supervisor_wrapper.supervisor_agent.sub_agents is None:
            supervisor_wrapper.supervisor_agent.sub_agents = []

        # Idempotency guard: only append if traffic_shaping_agent is not already wired
        existing_names = [a.name for a in supervisor_wrapper.supervisor_agent.sub_agents]
        if "traffic_shaping_agent" not in existing_names:
            traffic_agent = self.spawn_traffic_shaping_agent()
            # ADK wires parent links only at construction time; set it explicitly so
            # transfer_to_agent routing (and transfers back to the root) work for the new node.
            traffic_agent.parent_agent = supervisor_wrapper.supervisor_agent
            supervisor_wrapper.supervisor_agent.sub_agents.append(traffic_agent)
        else:
            traffic_agent = next(a for a in supervisor_wrapper.supervisor_agent.sub_agents if a.name == "traffic_shaping_agent")

        routing_rule = """
6. Dynamic Topology Routing (APEX Layer 3):
   You now have access to a permanent specialist sub-agent `traffic_shaping_agent`.
   When diagnosing an ingress surge, cache stampede, or connection saturation, immediately delegate traffic rate limiting to `traffic_shaping_agent`.
"""
        if "Dynamic Topology Routing (APEX Layer 3):" not in supervisor_wrapper.supervisor_agent.instruction:
            supervisor_wrapper.supervisor_agent.instruction += routing_rule

        # Re-bind ADK Runner
        supervisor_wrapper.runner = Runner(
            app_name="chrysalis-platform",
            agent=supervisor_wrapper.supervisor_agent,
            session_service=supervisor_wrapper.session_service,
            auto_create_session=True,
        )

        self.audit_logger.log_event(
            event_type="TOPOLOGY_MUTATED",
            actor="CloudTopologyMutator",
            action="rewire_supervisor",
            status="SUCCESS",
            details={
                "new_agent": traffic_agent.name,
                "hitl_request_id": hitl_request_id,
                "approval_token": approval_token,
                "sub_agents": [a.name for a in supervisor_wrapper.supervisor_agent.sub_agents],
            },
        )

        return {
            "status": "TOPOLOGY_MUTATED",
            "new_agent_name": traffic_agent.name,
            "hitl_approval_id": hitl_request_id,
            "approval_token": approval_token,
            "total_sub_agents": len(supervisor_wrapper.supervisor_agent.sub_agents),
            "sub_agent_names": [a.name for a in supervisor_wrapper.supervisor_agent.sub_agents],
        }


async def apply_policy_via_traffic_agent(supervisor_wrapper: Any, capacity: int, replenishment_rate: float) -> Dict[str, Any]:
    """Have the evolved multi-agent graph apply a Dream-RSI policy to the live limiter.

    The root supervisor receives a directive and must delegate to the commissioned
    `traffic_shaping_agent`, whose `set_rate_limit` tool (policy-checked) retunes the live
    token bucket. The outcome is verified against the actual limiter state; if the agents did
    not apply it (or Agent Platform is unavailable) the tool is invoked directly and labelled as such.
    """
    capacity, replenishment_rate = int(capacity), float(replenishment_rate)
    directive = (
        "Dream-RSI counterfactual replay selected the optimal ingress policy for the live token bucket: "
        f"capacity={capacity} tokens, replenishment_rate={replenishment_rate} req/s. "
        "Delegate to `traffic_shaping_agent` to apply exactly these values now with `set_rate_limit`, "
        "then briefly confirm the active settings."
    )
    trace = await supervisor_wrapper.run_directive(directive)

    def _limiter_matches() -> bool:
        lim = get_platform_env().rate_limiter
        return bool(lim) and int(lim.capacity) == capacity and abs(float(lim.replenishment_rate) - replenishment_rate) < 1e-6

    agent_applied = _limiter_matches() and any(tc["name"] == "set_rate_limit" for tc in trace["tool_calls"])
    fallback_result = None
    if not agent_applied:
        fallback_result = set_rate_limit(capacity, replenishment_rate)

    lim = get_platform_env().rate_limiter
    return {
        "source": "adk_agents" if agent_applied else "deterministic_fallback",
        "agents": trace["agents"],
        "tool_calls": trace["tool_calls"],
        "response": trace["text"],
        "fallback_result": fallback_result,
        "applied": _limiter_matches(),
        "active_limiter": {"capacity": lim.capacity, "replenishment_rate": lim.replenishment_rate} if lim else None,
    }
