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

"""Pydantic data schemas with Google Cloud governance metadata."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.config import PROJECT_ID, REGION


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


class GovernanceMetadata(BaseModel):
    """Google Cloud governance context attached to telemetry records."""

    cloud_project: str = PROJECT_ID
    region: str = REGION
    model_armor_scanned: bool = True
    kms_signed: bool = False
    policy_controller_evaluated: bool = True
    audit_logged: bool = True


class SystemMetrics(BaseModel):
    """Point-in-time SRE metrics snapshot of the target platform."""

    p99_latency_ms: float = Field(..., description="P99 ingress latency in ms")
    http_5xx_rate: float = Field(
        ..., description="Fraction of requests returning 5xx [0.0, 1.0]"
    )
    active_rps: float = Field(
        default=0.0, description="Current incoming requests per second"
    )
    db_pool_utilization: float = Field(
        ..., description="Database connection pool saturation [0.0, 1.0]"
    )
    cache_hit_ratio: float = Field(..., description="Cache hit ratio [0.0, 1.0]")
    cache_eviction_count: int = Field(
        default=0, description="Total cache keys evicted under LRU"
    )
    total_requests: int = Field(default=0, description="Total processed requests")
    status_2xx: int = Field(default=0)
    status_429: int = Field(default=0)
    status_5xx: int = Field(default=0)
    governance: GovernanceMetadata = Field(default_factory=GovernanceMetadata)


class ActionExecutionSpan(BaseModel):
    """A single agent tool execution with its pre/post system metrics."""

    span_id: str
    agent_name: str
    tool_name: str
    input_parameters: dict[str, Any]
    output_result: dict[str, Any]
    pre_state_metrics: SystemMetrics
    post_state_metrics: SystemMetrics
    cost_usd: float = 0.01
    execution_duration_ms: float = 50.0
    timestamp: str = Field(default_factory=utc_now)
    kms_signature: str | None = None


class OperationalPrinciple(BaseModel):
    """A distilled operational rule with contraindicated and recommended actions."""

    principle_id: str
    trigger_pattern: str
    contraindicated_actions: list[str]
    recommended_actions: list[str]
    confidence_score: float = 0.95
    source_incident_id: str = "INC-PLATFORM-001"
    created_at: str = Field(default_factory=utc_now)
    embedding: list[float] | None = None
    kms_signature_hex: str | None = None


class DynamicToolDefinition(BaseModel):
    """Metadata for a dynamically synthesized, governed tool."""

    tool_name: str
    description: str
    python_code: str
    input_schema: dict[str, Any]
    verification_hash: str
    kms_signature: str | None = None
    policy_controller_approved: bool = True
    created_at: str = Field(default_factory=utc_now)


class CounterfactualReplayResult(BaseModel):
    """Outcome of replaying recorded traffic against a candidate policy parameter."""

    policy_parameter_name: str
    tested_value: dict[str, Any]
    simulated_p99_latency_ms: float
    simulated_5xx_count: int
    simulated_database_max_load: float
    projected_cost_usd: float = 0.0
    is_pareto_optimal: bool = False
    cloud_engine: str = "Google BigQuery"
