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

"""Unit tests for BigQuery-backed Dream-RSI counterfactual replay engine."""
from app.config import PROJECT_ID
from app.evolution.bigquery_dream_rsi import BigQueryDreamRSIEngine


def test_bigquery_dream_rsi_ingestion_and_sweep() -> None:
    """Dream-RSI ingests request traces and runs the counterfactual policy sweep."""
    engine = BigQueryDreamRSIEngine(project_id=PROJECT_ID)
    logs = [
        {"seq_id": 1, "status_code": 200, "latency_ms": 25.0, "cache_miss": 0, "admitted": 1},
        {"seq_id": 2, "status_code": 500, "latency_ms": 3200.0, "cache_miss": 1, "admitted": 1},
        {"seq_id": 3, "status_code": 500, "latency_ms": 3200.0, "cache_miss": 1, "admitted": 1},
    ]

    loaded = engine.load_trajectory_data(logs)
    assert loaded == 3

    results, optimal, elapsed = engine.run_counterfactual_sweep(
        rates_to_test=[10.0, 20.0, 40.0, 80.0],
        capacities_to_test=[10, 20, 50],
    )

    assert len(results) == 12  # 4 rates * 3 capacities
    assert elapsed > 0.0
    assert "tested_value" in optimal
    assert optimal["simulated_5xx_count"] is not None
