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

"""Unit tests for benchmark_quality.py."""

import unittest

import benchmark_quality


class TestBenchmarkQuality(unittest.TestCase):
    """Tests dataset quality metrics and summary formatting helpers."""

    def test_macro_f1_calculation(self) -> None:
        # Verify macro-F1 equals 1.0 on perfect predictions.
        labels = ["World", "Sports"]
        self.assertAlmostEqual(
            benchmark_quality._compute_macro_f1(
                ["World", "Sports"], ["World", "Sports"], labels
            ),
            1.0,
        )

    def test_spearman_correlation(self) -> None:
        # Verify monotonic ranks yield +1.0 and reversed ranks yield -1.0.
        self.assertAlmostEqual(
            benchmark_quality._compute_spearman_correlation(
                [1.0, 2.0, 3.0], [10.0, 20.0, 30.0]
            ),
            1.0,
        )
        self.assertAlmostEqual(
            benchmark_quality._compute_spearman_correlation(
                [1.0, 2.0, 3.0], [30.0, 20.0, 10.0]
            ),
            -1.0,
        )

    def test_select_samples_supports_full_dataset(self) -> None:
        # Verify _select_samples returns all rows when num_samples <= 0.
        class _FakeDataset(list):

            def select(self, indices: range) -> list[int]:
                return [self[i] for i in indices]

        ds = _FakeDataset([10, 20, 30, 40])
        self.assertEqual(
            benchmark_quality._select_samples(ds, 0), [10, 20, 30, 40]
        )
        self.assertEqual(
            benchmark_quality._select_samples(ds, None), [10, 20, 30, 40]
        )
        self.assertEqual(benchmark_quality._select_samples(ds, 2), [10, 20])

    def test_build_quality_summary_rows_groups_by_dataset(self) -> None:
        # Verify flat quality metrics are pivoted into 1 row per dataset.
        flat = {
            "banking77_accuracy": 0.84,
            "banking77_macro_f1": 0.8042,
            "banking77_mean_confidence": 0.8611,
            "banking77_median_ms": 628.6,
            "boolq_accuracy": 0.92,
            "boolq_brier_score": 0.0734,
            "sst5_mae": 0.5552,
            "sst5_spearman": 0.8081,
        }
        rows = benchmark_quality.build_quality_summary_rows(flat)
        self.assertEqual(
            [r["dataset"] for r in rows], ["banking77", "boolq", "sst5"]
        )
        self.assertEqual(rows[0]["accuracy"], 0.84)
        self.assertEqual(rows[0]["median_ms"], 628.6)
        self.assertIsNone(rows[0]["mae"])
        self.assertEqual(rows[1]["brier_score"], 0.0734)
        self.assertEqual(rows[2]["spearman"], 0.8081)


if __name__ == "__main__":
    unittest.main()
