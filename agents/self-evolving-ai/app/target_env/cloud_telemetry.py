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

"""Google Cloud-integrated Telemetry Collector (Cloud Logging & Cloud Monitoring)."""
import threading
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import numpy as np
from app.config import PROJECT_ID, VERTEX_AI_AVAILABLE
from app.governance.cloud_log_writer import BackgroundCloudLogWriter
from app.target_env.cloudsql_service import CloudSqlDatabaseService
from app.target_env.memorystore_service import CloudMemorystoreService

try:
    from google.cloud import logging as gcp_logging
    GCP_LOGGING_AVAILABLE = True
except ImportError:
    GCP_LOGGING_AVAILABLE = False

try:
    GCP_MONITORING_AVAILABLE = True
except ImportError:
    GCP_MONITORING_AVAILABLE = False


class CloudTelemetryCollector:  # pylint: disable=too-many-instance-attributes
    """Thread-safe telemetry collector integrated directly with Google Cloud Logging & Monitoring."""

    def __init__(
        self,
        cache_service: Optional[CloudMemorystoreService] = None,
        db_service: Optional[CloudSqlDatabaseService] = None,
        project_id: str = PROJECT_ID,
    ):
        self.cache_service = cache_service
        self.db_service = db_service
        self.project_id = project_id
        self._lock = threading.Lock()

        # Telemetry metrics
        self.request_latencies_ms: List[float] = []
        self.total_requests: int = 0
        self.status_2xx_count: int = 0
        self.status_5xx_count: int = 0
        self.status_429_count: int = 0
        self.window_start_time: float = time.time()

        # Detailed request logs for BigQuery ingestion
        self.request_logs: List[Dict[str, Any]] = []
        self.action_spans: List[Dict[str, Any]] = []

        # Google Cloud Logging client (writes are batched off the request path)
        self._gcp_writer = None
        if GCP_LOGGING_AVAILABLE and VERTEX_AI_AVAILABLE:
            try:
                client = gcp_logging.Client(project=project_id)
                self._gcp_writer = BackgroundCloudLogWriter(client.logger("chimera-spans"))
            except Exception:  # pylint: disable=broad-exception-caught
                self._gcp_writer = None

    def record_request(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        request_id: str,
        endpoint: str,
        status_code: int,
        latency_ms: float,
        cache_miss: bool,
        admitted: bool = True,
    ) -> None:
        """Record an incoming HTTP request trace and stream to Cloud Logging."""
        iso_now = datetime.now(timezone.utc).isoformat()
        span_payload = {
            "timestamp": iso_now,
            "request_id": request_id,
            "endpoint": endpoint,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "cache_miss": int(cache_miss),
            "admitted": int(admitted),
            "cloud_provider": "Google Cloud",
            "gcp_project": self.project_id,
        }

        with self._lock:
            self.total_requests += 1
            if 200 <= status_code < 300:
                self.status_2xx_count += 1
            elif status_code == 429:
                self.status_429_count += 1
            elif status_code >= 500:
                self.status_5xx_count += 1

            self.request_latencies_ms.append(latency_ms)
            if len(self.request_latencies_ms) > 2000:
                self.request_latencies_ms = self.request_latencies_ms[-1000:]

            self.request_logs.append(span_payload)

        # Stream structured log entry to Google Cloud Logging (non-blocking, batched)
        if self._gcp_writer:
            severity = "ERROR" if status_code >= 500 else ("WARNING" if status_code == 429 else "INFO")
            self._gcp_writer.submit(span_payload, severity=severity)

    def record_action_span(self, span_dict: Dict[str, Any]) -> None:
        """Record an agent action execution span for AgentEvolver credit attribution."""
        with self._lock:
            self.action_spans.append(span_dict)

    def get_current_metrics(self) -> Dict[str, Any]:
        """Calculate real-time SRE metrics snapshot."""
        with self._lock:
            elapsed = max(time.time() - self.window_start_time, 0.001)
            active_rps = len(self.request_latencies_ms) / elapsed

            p99 = float(np.percentile(self.request_latencies_ms, 99)) if self.request_latencies_ms else 20.0
            total_reqs = self.status_2xx_count + self.status_5xx_count + self.status_429_count
            http_5xx_rate = (self.status_5xx_count / total_reqs) if total_reqs > 0 else 0.0

            cache_stats = self.cache_service.get_stats() if self.cache_service else {"hit_ratio": 1.0, "eviction_count": 0}
            db_stats = self.db_service.get_pool_stats() if self.db_service else {"active_connections": 0, "pool_utilization": 0.0}

            return {
                "p99_latency_ms": round(p99, 1),
                "http_5xx_rate": round(http_5xx_rate, 4),
                "active_rps": round(active_rps, 1),
                "db_pool_utilization": db_stats.get("pool_utilization", 0.0),
                "cache_hit_ratio": cache_stats.get("hit_ratio", 1.0),
                "cache_eviction_count": cache_stats.get("eviction_count", 0),
                "total_requests": self.total_requests,
                "status_2xx": self.status_2xx_count,
                "status_429": self.status_429_count,
                "status_5xx": self.status_5xx_count,
                "telemetry_sink": "Google Cloud Logging & Monitoring",
            }

    def get_request_logs(self) -> List[Dict[str, Any]]:
        """Return all recorded traces for BigQuery ingestion."""
        with self._lock:
            return list(self.request_logs)

    def get_action_spans(self) -> List[Dict[str, Any]]:
        """Return all agent action execution spans."""
        with self._lock:
            return list(self.action_spans)

    def start_new_window(self) -> None:
        """Reset active sliding-window HUD gauges while preserving historical request_logs for BigQuery."""
        with self._lock:
            self.request_latencies_ms.clear()
            self.status_2xx_count = 0
            self.status_5xx_count = 0
            self.status_429_count = 0
            self.window_start_time = time.time()

    def reset(self) -> None:
        """Reset telemetry sliding windows and buffers."""
        with self._lock:
            self.request_latencies_ms.clear()
            self.total_requests = 0
            self.status_2xx_count = 0
            self.status_5xx_count = 0
            self.status_429_count = 0
            self.request_logs.clear()
            self.action_spans.clear()
            self.window_start_time = time.time()
