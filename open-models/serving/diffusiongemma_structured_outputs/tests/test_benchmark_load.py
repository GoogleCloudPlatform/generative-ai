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

"""Unit tests for benchmark_load.py."""

import asyncio
import unittest
from unittest import mock

import benchmark_load
import config
import diffusiongemma_client
from test_diffusiongemma_client import FakeTokenizer


class TestBenchmarkLoad(unittest.TestCase):
    """Tests async HTTP load-testing helpers in benchmark_load.py."""

    def test_percentile_interpolation(self) -> None:
        # Verify p50 and p90 linear interpolation on a known sorted array.
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertAlmostEqual(
            benchmark_load._compute_percentile(vals, 50), 30.0
        )
        self.assertAlmostEqual(
            benchmark_load._compute_percentile(vals, 90), 46.0
        )

    def test_run_async_inside_running_event_loop(self) -> None:
        # Verify _run_async works even when an asyncio loop is already active.
        async def _sample_coro() -> int:
            await asyncio.sleep(0.001)
            return 42

        async def _notebook_cell_simulation() -> int:
            return benchmark_load._run_async(_sample_coro())

        self.assertEqual(
            benchmark_load._run_async(_notebook_cell_simulation()), 42
        )

    def test_run_concurrency_sweep_builds_unique_string_payloads(self) -> None:
        # Verify run_concurrency_sweep serializes unique string states cleanly.
        client = diffusiongemma_client.DiffusionGemmaClient(
            tokenizer=FakeTokenizer()
        )
        fake_resps = [
            {"usage": {"prompt_tokens": 300, "completion_tokens": 32}}
            for _ in range(4)
        ]
        with mock.patch.object(
            benchmark_load,
            "_execute_concurrent_requests_async",
            new=mock.AsyncMock(
                return_value=(fake_resps, [10.0, 20.0, 30.0, 40.0], 0)
            ),
        ) as mock_exec:
            metrics, rows = benchmark_load.run_concurrency_sweep(
                client=client,
                url="https://example.com/v1/ep:rawPredict",
                token="fake-tok",
                concurrencies=[2],
                requests_per_level=4,
                model=config.SERVED_MODEL_NAME,
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["succeeded"], 4)
        self.assertEqual(rows[0]["prompt_tokens_mean"], 300.0)
        self.assertEqual(rows[0]["output_tokens_mean"], 32.0)
        self.assertEqual(rows[0]["total_tokens"], 1328)
        self.assertIn("c2_rps", metrics)
        self.assertIn("c2_tokens_per_s", metrics)
        sent_payloads = mock_exec.call_args.args[2]
        self.assertEqual(len(sent_payloads), 4)
        self.assertNotEqual(sent_payloads[0], sent_payloads[1])


if __name__ == "__main__":
    unittest.main()
