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

"""Unit tests for benchmark_diffusiongemma.py CLI orchestrator."""

import sys
import tempfile
import unittest
from unittest import mock

import benchmark_diffusiongemma
import diffusiongemma_client
from test_diffusiongemma_client import FakeTokenizer


class TestBenchmarkDiffusionGemmaCLI(unittest.TestCase):
    """Tests the CLI orchestrator in benchmark_diffusiongemma.py."""

    @mock.patch("benchmark_diffusiongemma.benchmark_load.fetch_gcloud_bearer_token")
    @mock.patch("benchmark_diffusiongemma.diffusiongemma_client.resolve_endpoint")
    @mock.patch("benchmark_diffusiongemma.aiplatform")
    def test_main_writes_benchmark_report(
        self,
        mock_aiplatform: mock.MagicMock,
        mock_resolve_endpoint: mock.MagicMock,
        mock_fetch_token: mock.MagicMock,
    ) -> None:
        # Verify main() runs selected tasks and writes JSON output cleanly.
        fake_ep = mock.MagicMock()
        fake_ep.name = "12345"
        fake_ep.resource_name = "projects/1/locations/us-central1/endpoints/12345"
        fake_ep.dedicated_endpoint_dns = "12345.us-central1.prediction.vertexai.goog"
        mock_resolve_endpoint.return_value = fake_ep
        mock_fetch_token.return_value = "fake-token"

        client = diffusiongemma_client.DiffusionGemmaClient(
            tokenizer=FakeTokenizer()
        )
        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            test_argv = [
                "benchmark_diffusiongemma.py",
                "--project",
                "test-proj",
                "--tasks",
                "",
                "--concurrency",
                "",
                "--experiment",
                "",
                "--output",
                tmp.name,
            ]
            with (
                mock.patch.object(sys, "argv", test_argv),
                mock.patch.object(
                    diffusiongemma_client,
                    "DiffusionGemmaClient",
                    return_value=client,
                ),
            ):
                benchmark_diffusiongemma.main()

        mock_aiplatform.init.assert_called_once()


if __name__ == "__main__":
    unittest.main()
