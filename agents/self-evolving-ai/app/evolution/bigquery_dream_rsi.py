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

"""Dream-RSI: Google BigQuery-backed Counterfactual Replay Engine (Section 6.2).

When the `chimera_telemetry` dataset exists (see `scripts/setup_gcp.sh`), recorded request traces
are loaded into BigQuery with a per-run `run_id`, and the counterfactual policy sweep executes as a
single SQL query inside BigQuery. Without the dataset / credentials, the identical model runs on the
local in-memory buffer and results are labelled with the engine actually used.
"""

import time
import uuid
from typing import Any

from app.config import (
    BIGQUERY_DATASET,
    BIGQUERY_REQUESTS_TABLE,
    PROJECT_ID,
    VERTEX_AI_AVAILABLE,
)

try:
    from google.cloud import bigquery

    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False

ENGINE_BIGQUERY = "Google BigQuery (SQL counterfactual sweep)"
ENGINE_LOCAL = "Local replay engine (BigQuery dataset unavailable)"

# Counterfactual sweep executed inside BigQuery. Mirrors `_simulate_policy` exactly.
_SWEEP_SQL = """
WITH stats AS (
  SELECT COUNT(*) AS total, COUNTIF(cache_miss = 1) AS misses
  FROM `{table}`
  WHERE run_id = @run_id
),
grid AS (
  SELECT cap, rate FROM UNNEST(@caps) AS cap CROSS JOIN UNNEST(@rates) AS rate
),
sim AS (
  SELECT cap, rate, total,
         GREATEST(rate * IFNULL(SAFE_DIVIDE(misses, total), 0.5) / @sustained, cap / @burst) AS load
  FROM grid CROSS JOIN stats
)
SELECT
  cap,
  rate,
  ROUND(LEAST(load, 1.0), 2) AS sim_pool_load,
  IF(load <= 1.0, 0, CAST(ROUND(total * (1 - 1 / load) * 0.7) AS INT64)) AS sim_5xx,
  ROUND(IF(load <= 1.0, 25 + load * 30, 500 + (1 - 1 / load) * 3500), 1) AS sim_p99,
  load <= @headroom AS feasible
FROM sim
ORDER BY cap, rate
"""

_REQUESTS_SCHEMA = [
    ("run_id", "STRING"),
    ("seq_id", "INT64"),
    ("timestamp", "STRING"),
    ("request_id", "STRING"),
    ("endpoint", "STRING"),
    ("status_code", "INT64"),
    ("latency_ms", "FLOAT64"),
    ("cache_miss", "INT64"),
    ("admitted", "INT64"),
]


class BigQueryDreamRSIEngine:  # pylint: disable=too-many-instance-attributes
    """Zero-risk offline replay meta-simulator executing vectorized counterfactual sweeps in Google BigQuery."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        project_id: str = PROJECT_ID,
        dataset_id: str = BIGQUERY_DATASET,
        db_max_connections: int = 2,
        db_query_latency_s: float = 0.100,
        db_acquisition_timeout_s: float = 0.500,
        headroom_target: float = 0.85,
    ) -> None:
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.db_max_connections = db_max_connections
        self.db_query_latency_s = db_query_latency_s
        self.db_acquisition_timeout_s = db_acquisition_timeout_s
        self.headroom_target = headroom_target
        self._client: Any = None
        self._in_memory_records: list[dict[str, Any]] = []
        self.run_id: str = ""
        self.loaded_to_bigquery: bool = False
        self.engine: str = ENGINE_LOCAL
        self.last_error: str = ""

        if BIGQUERY_AVAILABLE and VERTEX_AI_AVAILABLE:
            try:
                self._client = bigquery.Client(project=project_id)
            except Exception:  # pylint: disable=broad-exception-caught
                self._client = None

    @property
    def table_id(self) -> str:
        """Fully-qualified BigQuery table ID for recorded request traces."""
        return f"{self.project_id}.{self.dataset_id}.{BIGQUERY_REQUESTS_TABLE}"

    def load_trajectory_data(self, request_logs: list[dict[str, Any]]) -> int:
        """Load recorded incident request stream into BigQuery (load job, tagged with a unique run_id)."""
        if not request_logs:
            request_logs = self._generate_synthetic_burst_logs()

        self._in_memory_records = list(request_logs)
        self.run_id = f"run_{uuid.uuid4().hex[:12]}"
        self.loaded_to_bigquery = False

        if self._client:
            rows = [
                {
                    "run_id": self.run_id,
                    "seq_id": seq,
                    "timestamp": str(log.get("timestamp", "")),
                    "request_id": str(log.get("request_id", f"req_{seq}")),
                    "endpoint": str(log.get("endpoint", "/checkout")),
                    "status_code": int(log.get("status_code", 200)),
                    "latency_ms": float(log.get("latency_ms", 50.0)),
                    "cache_miss": int(log.get("cache_miss", 1)),
                    "admitted": int(log.get("admitted", 1)),
                }
                for seq, log in enumerate(request_logs, start=1)
            ]
            try:
                job_config = bigquery.LoadJobConfig(
                    schema=[
                        bigquery.SchemaField(name, typ)
                        for name, typ in _REQUESTS_SCHEMA
                    ],
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                    create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
                )
                self._client.load_table_from_json(
                    rows, self.table_id, job_config=job_config
                ).result(timeout=60)
                self.loaded_to_bigquery = True
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Dataset not provisioned (run scripts/setup_gcp.sh) or no permission: local fallback
                self.last_error = f"{type(e).__name__}: {str(e)[:160]}"

        return len(self._in_memory_records)

    def _generate_synthetic_burst_logs(self) -> list[dict[str, Any]]:
        """Generate high-fidelity Black Friday burst traces."""
        logs = []
        for i in range(100):
            cache_miss = 1 if i < 70 else 0
            status = 500 if (cache_miss and i % 3 != 0) else 200
            latency = 3200.0 if status == 500 else (120.0 if cache_miss else 15.0)
            logs.append(
                {
                    "timestamp": f"2026-10-02T12:00:{i:02d}Z",
                    "request_id": f"burst_req_{i:03d}",
                    "endpoint": "/checkout",
                    "status_code": status,
                    "latency_ms": latency,
                    "cache_miss": cache_miss,
                    "admitted": 1,
                }
            )
        return logs

    @property
    def _sustained_capacity(self) -> float:
        # Sustained DB throughput = N / query_latency (2 / 0.1s = 20 queries/sec)
        return self.db_max_connections / self.db_query_latency_s

    @property
    def _burst_capacity(self) -> float:
        # Cold-miss burst tolerance = N * (timeout / query_latency) (2 * 5 = 10 concurrent misses)
        return self.db_max_connections * (
            self.db_acquisition_timeout_s / self.db_query_latency_s
        )

    def _result_row(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        cap: int,
        rate: float,
        pool_load: float,
        sim_5xx: int,
        sim_p99: float,
        feasible: bool,
        engine: str,
    ) -> dict[str, Any]:
        return {
            "policy_parameter_name": "token_replenishment_rate",
            "tested_value": {"capacity": int(cap), "rate_req_sec": float(rate)},
            "simulated_p99_latency_ms": float(sim_p99),
            "simulated_5xx_count": int(sim_5xx),
            "simulated_database_max_load": float(pool_load),
            "projected_cost_usd": 0.0,
            "is_pareto_optimal": bool(feasible),
            "engine": engine,
        }

    def _sweep_in_bigquery(
        self, rates: list[float], caps: list[int]
    ) -> list[dict[str, Any]]:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("run_id", "STRING", self.run_id),
                bigquery.ArrayQueryParameter("caps", "INT64", [int(c) for c in caps]),
                bigquery.ArrayQueryParameter(
                    "rates", "FLOAT64", [float(r) for r in rates]
                ),
                bigquery.ScalarQueryParameter(
                    "sustained", "FLOAT64", self._sustained_capacity
                ),
                bigquery.ScalarQueryParameter("burst", "FLOAT64", self._burst_capacity),
                bigquery.ScalarQueryParameter(
                    "headroom", "FLOAT64", self.headroom_target
                ),
            ],
            use_query_cache=False,
        )
        rows = self._client.query(
            _SWEEP_SQL.format(table=self.table_id), job_config=job_config
        ).result(timeout=60)
        return [
            self._result_row(
                r["cap"],
                r["rate"],
                r["sim_pool_load"],
                r["sim_5xx"],
                r["sim_p99"],
                r["feasible"],
                ENGINE_BIGQUERY,
            )
            for r in rows
        ]

    def _sweep_locally(
        self, rates: list[float], caps: list[int]
    ) -> list[dict[str, Any]]:
        total_requests = len(self._in_memory_records)
        total_misses = sum(
            1 for r in self._in_memory_records if r.get("cache_miss") == 1
        )
        miss_ratio = (total_misses / total_requests) if total_requests > 0 else 0.5

        results = []
        for cap in caps:
            for rate in rates:
                # Burst check assumes a cold cache (every admitted request misses); sustained check
                # uses the observed miss ratio from the recorded trajectory.
                load = max(
                    (rate * miss_ratio) / self._sustained_capacity,
                    cap / self._burst_capacity,
                )
                if load <= 1.0:
                    sim_5xx, sim_p99 = 0, 25.0 + (load * 30.0)
                else:
                    excess_ratio = 1.0 - (1.0 / load)
                    sim_5xx = int(round(total_requests * excess_ratio * 0.7))
                    sim_p99 = 500.0 + (excess_ratio * 3500.0)
                # SLO-feasible frontier: zero 5xx with >= 15% pool headroom
                results.append(
                    self._result_row(
                        cap,
                        rate,
                        round(min(load, 1.0), 2),
                        sim_5xx,
                        round(sim_p99, 1),
                        sim_5xx == 0 and load <= self.headroom_target,
                        ENGINE_LOCAL,
                    )
                )
        return results

    def run_counterfactual_sweep(
        self,
        rates_to_test: list[float] | None = None,
        capacities_to_test: list[int] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], float]:
        """Run the sweep over token bucket parameters to discover the optimal SLO-feasible policy."""
        if rates_to_test is None:
            rates_to_test = [float(r) for r in range(5, 205, 5)]
        if capacities_to_test is None:
            capacities_to_test = [5, 10, 20, 30, 42, 50, 75, 100]

        start_time = time.perf_counter()
        results: list[dict[str, Any]] = []
        if self.loaded_to_bigquery:
            try:
                results = self._sweep_in_bigquery(rates_to_test, capacities_to_test)
                self.engine = ENGINE_BIGQUERY
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.last_error = f"{type(e).__name__}: {str(e)[:160]}"
                results = []
        if not results:
            results = self._sweep_locally(rates_to_test, capacities_to_test)
            self.engine = ENGINE_LOCAL
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        pareto_candidates = [r for r in results if r["is_pareto_optimal"]]
        if pareto_candidates:
            # Maximize sustained throughput first, then burst tolerance
            optimal_policy = max(
                pareto_candidates,
                key=lambda r: (
                    r["tested_value"]["rate_req_sec"],
                    r["tested_value"]["capacity"],
                ),
            )
        else:
            optimal_policy = min(
                results,
                key=lambda r: (
                    r["simulated_5xx_count"],
                    r["simulated_database_max_load"],
                ),
            )

        return results, optimal_policy, elapsed_ms
