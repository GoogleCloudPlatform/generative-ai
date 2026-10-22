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

from typing import Any

from google.adk.tools import FunctionTool

from app.evolution.cloud_principle_store import CloudPrincipleStore
from app.runtime_registry import get_platform_env

_principle_store: CloudPrincipleStore | None = None  # pylint: disable=invalid-name


def get_principle_store() -> CloudPrincipleStore:
    """Lazy-load the CloudPrincipleStore to prevent slow remote calls during import."""
    global _principle_store  # pylint: disable=global-statement
    if _principle_store is None:
        _principle_store = CloudPrincipleStore()
    return _principle_store


def read_system_metrics() -> dict[str, Any]:
    """Read real-time SRE metrics (P99 latency, 5xx rate, active RPS) from Cloud Telemetry."""
    return get_platform_env().telemetry.get_current_metrics()


def inspect_cache_status() -> dict[str, Any]:
    """Inspect Cloud Memorystore for Redis key capacity, eviction counts, and hit ratio."""
    return get_platform_env().cache.get_stats()


def inspect_db_pool() -> dict[str, Any]:
    """Inspect Cloud SQL database connection pool saturation, active connections, and waiting threads."""
    return get_platform_env().db.get_pool_stats()


def retrieve_historical_principles(incident_context: str) -> list[dict[str, Any]]:
    """Query Self-Navigating Agent Platform vector memory for past failure principles and contraindicated actions."""
    store = get_principle_store()
    results = store.query_similar_principles(incident_context, top_k=2)
    output = []
    for p, score in results:
        output.append(
            {
                "principle_id": p.principle_id,
                "trigger_pattern": p.trigger_pattern,
                "contraindicated_actions": p.contraindicated_actions,
                "recommended_actions": p.recommended_actions,
                "confidence_score": p.confidence_score,
                "similarity_score": round(score, 3),
                "kms_signed": (p.kms_signature is not None),
            }
        )
    return output


tool_read_metrics = FunctionTool(read_system_metrics)
tool_inspect_cache = FunctionTool(inspect_cache_status)
tool_inspect_db = FunctionTool(inspect_db_pool)
tool_retrieve_principles = FunctionTool(retrieve_historical_principles)

DIAGNOSTIC_TOOLS = [
    tool_read_metrics,
    tool_inspect_cache,
    tool_inspect_db,
    tool_retrieve_principles,
]
