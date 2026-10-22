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

"""Deterministic Policy-as-Code Controller (Google Cloud Policy Controller / OPA style)."""

from typing import Any

from pydantic import BaseModel, Field

from app.config import POLICY_MAX_CAPACITY, POLICY_MIN_ADMIT_RATE


class PolicyEvaluationResult(BaseModel):
    """Verdict of a policy evaluation, including any violations and the enforced bounds."""

    allowed: bool
    policy_id: str
    violations: list[str] = Field(default_factory=list)
    enforced_bounds: dict[str, Any] = Field(default_factory=dict)


class CloudPolicyController:
    """Evaluates invariant policies before runtime mutations or dynamic tool injections."""

    FORBIDDEN_ACTIONS = {
        "reboot_database",
        "restart_database",
        "drop_database",
        "kill_connections",
        "flush_db_connections",
        "truncate_tables",
        "disable_rate_limiting",
    }

    ALLOWED_REMEDIATIONS = {
        "token_bucket_rate_limiter",
        "deploy_token_bucket_rate_limiter",
        "throttle_ingress_boundary",
        "shed_non_critical_load",
        "prewarm_cache",
        "scale_read_replica",
    }

    def __init__(
        self,
        min_rate: float = POLICY_MIN_ADMIT_RATE,
        max_capacity: int = POLICY_MAX_CAPACITY,
    ):
        self.min_rate = min_rate
        self.max_capacity = max_capacity
        self.total_evaluations: int = 0
        self.total_rejections: int = 0

    def reset_counters(self) -> None:
        """Reset evaluation statistics (policy invariants themselves are unchanged)."""
        self.total_evaluations = 0
        self.total_rejections = 0

    def evaluate_rate_limiter_policy(
        self,
        capacity: int,
        replenishment_rate: float,
        context: dict[str, Any] | None = None,  # pylint: disable=unused-argument
    ) -> PolicyEvaluationResult:
        """Evaluate whether a rate limiter configuration satisfies enterprise SLA invariants."""
        self.total_evaluations += 1
        violations = []

        # Invariant 1: Rate limit cannot drop below business SLA floor
        if replenishment_rate < self.min_rate:
            violations.append(
                f"[SLA_FLOOR_BREACH] Replenishment rate {replenishment_rate} req/s violates minimum guaranteed SLA floor of {self.min_rate} req/s"
            )

        # Invariant 2: Capacity cannot exceed maximum buffer ceiling (prevents memory exhaustion)
        if capacity > self.max_capacity:
            violations.append(
                f"[CAPACITY_CEILING_BREACH] Burst capacity {capacity} exceeds allowed ceiling of {self.max_capacity}"
            )

        if capacity <= 0:
            violations.append(
                "[INVALID_CAPACITY] Burst capacity must be strictly positive"
            )

        is_allowed = len(violations) == 0
        if not is_allowed:
            self.total_rejections += 1

        return PolicyEvaluationResult(
            allowed=is_allowed,
            policy_id="POL-SRE-INVARIANT-001",
            violations=violations,
            enforced_bounds={
                "min_rate_req_sec": self.min_rate,
                "max_capacity": self.max_capacity,
                "tested_rate": replenishment_rate,
                "tested_capacity": capacity,
            },
        )

    def evaluate_action_admissibility(self, action_name: str) -> PolicyEvaluationResult:
        """Evaluate if an action proposed by an agent is permitted under enterprise security policy."""
        self.total_evaluations += 1
        violations = []

        norm_action = action_name.lower().strip()
        if norm_action in self.FORBIDDEN_ACTIONS:
            violations.append(
                f"[FORBIDDEN_DESTRUCTIVE_ACTION] Action '{action_name}' is strictly prohibited by security guardrail"
            )

        is_allowed = len(violations) == 0
        if not is_allowed:
            self.total_rejections += 1

        return PolicyEvaluationResult(
            allowed=is_allowed,
            policy_id="POL-ACTION-WHITELIST-002",
            violations=violations,
            enforced_bounds={"allowed_actions": list(self.ALLOWED_REMEDIATIONS)},
        )
