#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for monitoring.py."""

from datetime import datetime, timezone
import unittest
from unittest import mock

import monitoring


class TestMonitoring(unittest.TestCase):
    """Tests Cloud Monitoring GPU/CPU metric alignment in monitoring.py."""

    def test_fetch_endpoint_utilization_and_attach_to_sweep(self) -> None:
        # Verify Cloud Monitoring metric normalization and stage alignment.
        t0 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 10, 19, 12, 2, 0, tzinfo=timezone.utc)

        def _make_ts(unit: str, val: float) -> mock.MagicMock:
            pt = mock.MagicMock()
            pt.interval.end_time = datetime(
                2026, 10, 19, 12, 1, 0, tzinfo=timezone.utc
            )
            pt.value.double_value = val
            pt.value.int64_value = 0
            ts = mock.MagicMock()
            ts.unit = unit
            ts.points = [pt]
            return ts

        fake_client = mock.MagicMock()

        def _side_effect(request: dict[str, object]) -> list[mock.MagicMock]:
            flt = str(request["filter"])
            if "accelerator/duty_cycle" in flt:
                return [_make_ts("%", 94.5)]
            if "accelerator/memory/bytes_used" in flt:
                return [_make_ts("By", 18.5 * (1024.0**3))]
            if "cpu/utilization" in flt:
                return [_make_ts("1", 0.35)]
            if "online/memory/bytes_used" in flt:
                return [_make_ts("By", 6.0 * (1024.0**3))]
            return []

        fake_client.list_time_series.side_effect = _side_effect
        summary, rows = monitoring.fetch_endpoint_utilization_metrics(
            project="test-proj",
            endpoint_id="12345",
            start_time=t0,
            end_time=t1,
            client=fake_client,
        )
        self.assertEqual(summary["gpu_duty_cycle_pct_max"], 94.5)
        self.assertEqual(summary["cpu_utilization_pct_mean"], 35.0)
        self.assertEqual(summary["gpu_vram_gib_max"], 18.5)
        self.assertEqual(len(rows), 1)

        sweep_rows = [
            {
                "concurrency": 4,
                "start_utc": t0.isoformat(),
                "end_utc": t1.isoformat(),
            }
        ]
        monitoring.attach_utilization_to_sweep(sweep_rows, rows)
        self.assertEqual(sweep_rows[0]["gpu_duty_cycle_pct"], 94.5)
        self.assertEqual(sweep_rows[0]["cpu_utilization_pct"], 35.0)

    def test_dcgm_prometheus_gpu_metrics_alignment(self) -> None:
        # Verify prometheus_target DCGM metrics align :57 scrapes to :00 buckets.
        t0 = datetime(2026, 10, 20, 5, 53, 50, tzinfo=timezone.utc)
        t1 = datetime(2026, 10, 20, 5, 56, 9, tzinfo=timezone.utc)

        def _make_pt(sec_dt: datetime, val: float) -> mock.MagicMock:
            pt = mock.MagicMock()
            pt.interval.end_time = sec_dt
            pt.value.double_value = val
            pt.value.int64_value = 0
            return pt

        fake_client = mock.MagicMock()

        def _side_effect(request: dict[str, object]) -> list[mock.MagicMock]:
            flt = str(request["filter"])
            ts = mock.MagicMock()
            ts.unit = ""
            if "vertex_dcgm_fi_dev_gpu_util/gauge" in flt:
                self.assertIn('resource.type = "prometheus_target"', flt)
                self.assertIn(
                    'metric.labels.endpoint_id = "diffusiongemma-vllm"', flt
                )
                ts.points = [
                    _make_pt(
                        datetime(2026, 10, 20, 5, 54, 57, tzinfo=timezone.utc),
                        90.0,
                    ),
                    _make_pt(
                        datetime(2026, 10, 20, 5, 55, 57, tzinfo=timezone.utc),
                        89.0,
                    ),
                ]
                return [ts]
            if "vertex_dcgm_fi_dev_fb_used/gauge" in flt:
                ts.points = [
                    _make_pt(
                        datetime(2026, 10, 20, 5, 54, 57, tzinfo=timezone.utc),
                        20480.0,
                    )
                ]
                return [ts]
            if "vertex_dcgm_fi_dev_power_usage/gauge" in flt:
                ts.points = [
                    _make_pt(
                        datetime(2026, 10, 20, 5, 54, 57, tzinfo=timezone.utc),
                        72.0,
                    )
                ]
                return [ts]
            return []

        fake_client.list_time_series.side_effect = _side_effect
        summary, rows = monitoring.fetch_endpoint_utilization_metrics(
            project="test-proj",
            endpoint_id="diffusiongemma-vllm",
            start_time=t0,
            end_time=t1,
            client=fake_client,
        )
        self.assertEqual(summary["gpu_duty_cycle_pct_mean"], 89.5)
        self.assertEqual(summary["gpu_vram_gib_max"], 20.0)
        self.assertEqual(summary["gpu_power_w_max"], 72.0)

        sweep_rows = [
            {
                "concurrency": 4,
                "start_utc": t0.isoformat(),
                "end_utc": t1.isoformat(),
            }
        ]
        monitoring.attach_utilization_to_sweep(sweep_rows, rows)
        self.assertEqual(sweep_rows[0]["gpu_duty_cycle_pct"], 89.5)
        self.assertEqual(sweep_rows[0]["gpu_vram_gib"], 20.0)
        self.assertEqual(sweep_rows[0]["gpu_power_w"], 72.0)


if __name__ == "__main__":
    unittest.main()
