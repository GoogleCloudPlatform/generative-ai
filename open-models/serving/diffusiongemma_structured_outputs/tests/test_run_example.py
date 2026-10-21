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

"""Unit tests for run_example.py."""

import sys
import unittest
from unittest import mock

import diffusiongemma_client
import run_example
from test_diffusiongemma_client import FakeTokenizer, _make_logprobs_response


class TestRunExample(unittest.TestCase):
    """Tests example schema constants and CLI runner in run_example.py."""

    def test_example_questions_and_state_are_valid(self) -> None:
        # Verify EXAMPLE_STATE and EXAMPLE_QUESTIONS compile cleanly.
        self.assertTrue(run_example.EXAMPLE_STATE.strip())
        client = diffusiongemma_client.DiffusionGemmaClient(
            tokenizer=FakeTokenizer()
        )
        compiled = client.build_canvas(run_example.EXAMPLE_QUESTIONS)
        self.assertEqual(len(compiled["slots"]), 4)
        slot_names = [s["name"] for s in compiled["slots"]]
        self.assertEqual(
            slot_names,
            [
                "routing_team",
                "severity_level",
                "churn_or_expansion_risk",
                "requires_immediate_page",
            ],
        )

    @mock.patch("run_example.diffusiongemma_client.resolve_endpoint")
    @mock.patch("run_example.aiplatform")
    def test_main_executes_structured_read(
        self,
        mock_aiplatform: mock.MagicMock,
        mock_resolve_endpoint: mock.MagicMock,
    ) -> None:
        # Verify main() runs single-step structured diffusion read cleanly.
        client = diffusiongemma_client.DiffusionGemmaClient(
            tokenizer=FakeTokenizer()
        )
        compiled = client.build_canvas(run_example.EXAMPLE_QUESTIONS)

        fake_ep = mock.MagicMock()
        mock_resolve_endpoint.return_value = fake_ep

        structured_resp = mock.MagicMock()
        structured_resp.status_code = 200
        structured_resp.json.return_value = _make_logprobs_response(
            compiled["canvas_width"],
            {s["pos"]: [(s["label_ids"][0], 0.0)] for s in compiled["slots"]},
        )
        fake_ep.raw_predict.side_effect = [structured_resp]

        test_argv = [
            "run_example.py",
            "--project",
            "test-project",
            "--runs",
            "1",
        ]
        with (
            mock.patch.object(sys, "argv", test_argv),
            mock.patch.object(
                diffusiongemma_client,
                "DiffusionGemmaClient",
                return_value=client,
            ),
        ):
            run_example.main()

        mock_aiplatform.init.assert_called_once()
        self.assertEqual(fake_ep.raw_predict.call_count, 1)


if __name__ == "__main__":
    unittest.main()
