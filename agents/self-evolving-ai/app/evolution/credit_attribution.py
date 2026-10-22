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

"""AgentEvolver: Fine-Grained Step-Level Credit Attribution Engine (Section 6.2)."""
import math
from typing import List, Dict, Any
from pydantic import BaseModel


class StepCreditAttribution(BaseModel):
    """Credit score and verdict attributed to a single agent execution span."""

    span_id: str
    action_name: str
    pre_health: float
    post_health: float
    health_delta: float
    action_cost_usd: float
    credit_score: float
    verdict: str  # REWARDED (+) or PENALIZED (-)


class CreditAttributionEngine:
    """Computes mathematical Shapley-inspired credit scores over agent execution spans."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        w1: float = 0.35,  # Latency weight
        w2: float = 0.40,  # 5xx error weight
        w3: float = 0.25,  # DB pool utilization weight
        target_latency_ms: float = 50.0,
        alpha: float = 2.5,
        beta: float = 1.0,
    ):
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.target_latency_ms = target_latency_ms
        self.alpha = alpha
        self.beta = beta

    def compute_system_health(self, p99_latency_ms: float, http_5xx_rate: float, db_pool_utilization: float) -> float:
        """Compute composite system health score H(S_t) in range [0.0, 1.0]. Lower is healthier."""
        norm_latency = min(p99_latency_ms / (self.target_latency_ms * 4.0), 1.0)
        h = (self.w1 * norm_latency) + (self.w2 * http_5xx_rate) + (self.w3 * db_pool_utilization)
        return round(float(min(max(h, 0.0), 1.0)), 4)

    def attribute_span_credit(self, span: Dict[str, Any]) -> StepCreditAttribution:
        """Compute credit score C(a_t) = tanh(alpha * delta_H - beta * Cost)."""
        pre_m = span.get("pre_state_metrics", {})
        post_m = span.get("post_state_metrics", {})

        h_pre = self.compute_system_health(
            pre_m.get("p99_latency_ms", 1500.0),
            pre_m.get("http_5xx_rate", 0.40),
            pre_m.get("db_pool_utilization", 1.0),
        )
        h_post = self.compute_system_health(
            post_m.get("p99_latency_ms", 30.0),
            post_m.get("http_5xx_rate", 0.0),
            post_m.get("db_pool_utilization", 0.0),
        )

        delta_h = h_pre - h_post  # Positive means health improved
        cost_usd = span.get("cost_usd", 0.01)

        raw_credit = (self.alpha * delta_h) - (self.beta * cost_usd)
        credit_score = round(math.tanh(raw_credit), 4)

        verdict = "REWARDED (+)" if credit_score > 0 else "PENALIZED (-)"

        return StepCreditAttribution(
            span_id=span.get("span_id", "span_unknown"),
            action_name=span.get("tool_name", "action_unknown"),
            pre_health=h_pre,
            post_health=h_post,
            health_delta=round(delta_h, 4),
            action_cost_usd=cost_usd,
            credit_score=credit_score,
            verdict=verdict,
        )

    def attribute_trajectory_credits(self, spans: List[Dict[str, Any]]) -> List[StepCreditAttribution]:
        """Process an entire trajectory of action execution spans."""
        return [self.attribute_span_credit(s) for s in spans]
