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

"""Unit tests for diffusiongemma_client.py."""

import math
import unittest
from unittest import mock

import config
import diffusiongemma_client
import run_example


class FakeTokenizer:
    """Deterministic single-token fake tokenizer for offline unit tests."""

    def __init__(self) -> None:
        self.pad_token_id = 0
        self._vocab: dict[str, int] = {
            "<pad>": 0,
            "<|Reserved_2|>": 69,
            "true": 100,
            "false": 101,
        }
        # Map A-Z to token IDs 200..225 and 0-9 to token IDs 300..309.
        for i in range(26):
            self._vocab[chr(ord("A") + i)] = 200 + i
        for d in range(10):
            self._vocab[str(d)] = 300 + d

    def convert_tokens_to_ids(self, token: str) -> int:
        return self._vocab[token]

    def encode(
        self, text: str, add_special_tokens: bool = False
    ) -> list[int]:
        del add_special_tokens
        if text in self._vocab:
            return [self._vocab[text]]
        # Encode arbitrary structural characters deterministically by ord().
        return [1000 + ord(ch) for ch in text]


def _make_logprobs_response(
    canvas_width: int,
    slot_logprobs: dict[int, list[tuple[int, float]]],
) -> dict:
    """Builds a mock vLLM /v1/chat/completions response with top_logprobs."""
    content = []
    for pos in range(canvas_width):
        cands = slot_logprobs.get(pos, [])
        content.append(
            {
                "token": "token_id:0",
                "logprob": 0.0,
                "top_logprobs": [
                    {"token": f"token_id:{tid}", "logprob": lp}
                    for tid, lp in cands
                ],
            }
        )
    return {
        "model": config.SERVED_MODEL_NAME,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "{}"},
                "logprobs": {"content": content},
            }
        ],
        "usage": {"prompt_tokens": 128, "completion_tokens": canvas_width},
    }


class TestDiffusionGemmaClientSchema(unittest.TestCase):
    """Tests schema compilation and masked JSON canvas construction."""

    def setUp(self) -> None:
        self.tok = FakeTokenizer()
        self.client = diffusiongemma_client.DiffusionGemmaClient(
            tokenizer=self.tok
        )

    def test_compile_choice_question(self) -> None:
        # Verify a 3-option choice question maps to single-token letters A-C.
        schema = {
            "team": {
                "type": "choice",
                "instructions": "Pick a team.",
                "criteria": {
                    "sec": "security",
                    "bill": "billing",
                    "infra": "infrastructure",
                },
            }
        }
        compiled = self.client.build_canvas(schema)
        self.assertEqual(len(compiled["slots"]), 1)
        slot = compiled["slots"][0]
        self.assertEqual(slot["name"], "team")
        self.assertEqual(slot["type"], "choice")
        self.assertEqual(slot["keys"], ["sec", "bill", "infra"])
        self.assertEqual(slot["label_ids"], [200, 201, 202])
        # Verify the mask token ID (69) sits at the recorded slot position.
        self.assertEqual(compiled["seed_canvas"][slot["pos"]], 69)

    def test_compile_score_question(self) -> None:
        # Verify a 5-level score question maps to single-digit tokens 0-4.
        schema = {
            "severity": {
                "type": "score",
                "instructions": "Rate severity.",
                "criteria": ["v0", "v1", "v2", "v3", "v4"],
            }
        }
        compiled = self.client.build_canvas(schema)
        slot = compiled["slots"][0]
        self.assertEqual(slot["type"], "score")
        self.assertEqual(slot["label_ids"], [300, 301, 302, 303, 304])
        self.assertEqual(
            slot["legend"],
            {"0": "v0", "1": "v1", "2": "v2", "3": "v3", "4": "v4"},
        )
        self.assertEqual(compiled["seed_canvas"][slot["pos"]], 69)

    def test_compile_boolean_question(self) -> None:
        # Verify a boolean question uses [true_id, false_id] as label_ids.
        schema = {
            "urgent": {
                "type": "boolean",
                "instructions": "Is this urgent?",
            }
        }
        compiled = self.client.build_canvas(schema)
        slot = compiled["slots"][0]
        self.assertEqual(slot["type"], "boolean")
        self.assertEqual(slot["label_ids"], [100, 101])
        self.assertEqual(compiled["seed_canvas"][slot["pos"]], 69)

    def test_compile_mixed_multi_question_schema(self) -> None:
        # Verify mixed 4-question schema assigns distinct mask positions.
        compiled = self.client.build_canvas(run_example.EXAMPLE_QUESTIONS)
        self.assertEqual(len(compiled["slots"]), 4)
        positions = [s["pos"] for s in compiled["slots"]]
        self.assertEqual(len(set(positions)), 4)
        for pos in positions:
            self.assertEqual(compiled["seed_canvas"][pos], 69)
        self.assertEqual(
            compiled["all_label_ids"], sorted(set(compiled["all_label_ids"]))
        )

    def test_canvas_width_rounds_up_to_multiple_of_16(self) -> None:
        # Verify canvas_width is a multiple of 16 and matches seed_canvas len.
        compiled = self.client.build_canvas(run_example.EXAMPLE_QUESTIONS)
        self.assertEqual(compiled["canvas_width"] % 16, 0)
        self.assertGreaterEqual(compiled["canvas_width"], 16)
        self.assertEqual(
            len(compiled["seed_canvas"]), compiled["canvas_width"]
        )

    def test_unsupported_question_type_raises_value_error(self) -> None:
        # Verify unknown question types raise ValueError immediately.
        bad_schema = {
            "bad": {"type": "freeform", "instructions": "Unsupported."}
        }
        with self.assertRaises(ValueError):
            self.client.build_canvas(bad_schema)


class TestDiffusionGemmaClientRequest(unittest.TestCase):
    """Tests vLLM request payload construction."""

    def setUp(self) -> None:
        self.client = diffusiongemma_client.DiffusionGemmaClient(
            tokenizer=FakeTokenizer()
        )
        self.compiled = self.client.build_canvas(
            run_example.EXAMPLE_QUESTIONS
        )

    def test_build_request_vllm_xargs_and_top_level_fields(self) -> None:
        # Verify vllm_xargs and top-level logprob fields match vLLM 0.31.0.
        req = self.client.build_request("ticket text", self.compiled)
        self.assertEqual(req["model"], config.SERVED_MODEL_NAME)
        self.assertEqual(
            req["messages"][0]["content"], diffusiongemma_client.SYSTEM_PROMPT
        )
        self.assertEqual(req["max_tokens"], self.compiled["canvas_width"])
        self.assertTrue(req["logprobs"])
        self.assertEqual(
            req["top_logprobs"], len(self.compiled["all_label_ids"])
        )
        self.assertEqual(
            req["logprob_token_ids"], self.compiled["all_label_ids"]
        )
        self.assertTrue(req["return_tokens_as_token_ids"])
        self.assertEqual(
            req["chat_template_kwargs"], {"enable_thinking": False}
        )
        xargs = req["vllm_xargs"]
        self.assertEqual(
            xargs["diffusion_seed_canvas"], self.compiled["seed_canvas"]
        )
        self.assertEqual(xargs["diffusion_max_steps"], 1)
        self.assertTrue(xargs["diffusion_read_only"])
        self.assertTrue(xargs["diffusion_constrained"])
        self.assertEqual(
            xargs["diffusion_canvas_length"], self.compiled["canvas_width"]
        )

    def test_build_request_omits_temperature(self) -> None:
        # Ensure temperature is omitted since vLLM 0.31.0 rejects it.
        req = self.client.build_request("ticket text", self.compiled)
        self.assertNotIn("temperature", req)


class TestDiffusionGemmaClientParseResponse(unittest.TestCase):
    """Tests logprob softmax, Shannon entropy confidence, and score math."""

    def setUp(self) -> None:
        self.client = diffusiongemma_client.DiffusionGemmaClient(
            tokenizer=FakeTokenizer()
        )

    def test_parse_choice_probabilities_and_argmax(self) -> None:
        # Feed known logprobs log(0.7), log(0.2), log(0.1) for A, B, C.
        schema = {
            "team": {
                "type": "choice",
                "instructions": "Pick a team.",
                "criteria": {"sec": "a", "bill": "b", "infra": "c"},
            }
        }
        compiled = self.client.build_canvas(schema)
        pos = compiled["slots"][0]["pos"]
        raw = _make_logprobs_response(
            compiled["canvas_width"],
            {
                pos: [
                    (200, math.log(0.7)),
                    (201, math.log(0.2)),
                    (202, math.log(0.1)),
                ]
            },
        )
        parsed = self.client.parse_response(raw, compiled)
        ans = parsed["answers"]["team"]
        self.assertEqual(ans["choice"], "sec")
        self.assertAlmostEqual(ans["probabilities"]["sec"], 0.7, places=5)
        self.assertAlmostEqual(ans["probabilities"]["bill"], 0.2, places=5)
        self.assertAlmostEqual(ans["probabilities"]["infra"], 0.1, places=5)

    def test_parse_score_expected_value(self) -> None:
        # Verify expected score equals sum(i * p_i) across levels 0, 1, 2.
        schema = {
            "sev": {
                "type": "score",
                "instructions": "Rate severity.",
                "criteria": ["low", "med", "high"],
            }
        }
        compiled = self.client.build_canvas(schema)
        pos = compiled["slots"][0]["pos"]
        # Probabilities 0.1, 0.3, 0.6 give expected score
        # 0*0.1 + 1*0.3 + 2*0.6 = 1.5.
        raw = _make_logprobs_response(
            compiled["canvas_width"],
            {
                pos: [
                    (300, math.log(0.1)),
                    (301, math.log(0.3)),
                    (302, math.log(0.6)),
                ]
            },
        )
        parsed = self.client.parse_response(raw, compiled)
        ans = parsed["answers"]["sev"]
        self.assertAlmostEqual(ans["score"], 1.5, places=5)

    def test_parse_boolean_probability(self) -> None:
        # Verify boolean probability equals P(true) / (P(true) + P(false)).
        schema = {
            "flag": {"type": "boolean", "instructions": "True or false?"}
        }
        compiled = self.client.build_canvas(schema)
        pos = compiled["slots"][0]["pos"]
        raw = _make_logprobs_response(
            compiled["canvas_width"],
            {pos: [(100, math.log(0.8)), (101, math.log(0.2))]},
        )
        parsed = self.client.parse_response(raw, compiled)
        self.assertAlmostEqual(
            parsed["answers"]["flag"]["boolean"], 0.8, places=5
        )

    def test_shannon_entropy_confidence_bounds(self) -> None:
        # Verify uniform logprobs yield confidence 0.0 and peaked yields 1.0.
        schema = {
            "team": {
                "type": "choice",
                "instructions": "Pick.",
                "criteria": {"a": "1", "b": "2", "c": "3"},
            }
        }
        compiled = self.client.build_canvas(schema)
        pos = compiled["slots"][0]["pos"]
        uniform_raw = _make_logprobs_response(
            compiled["canvas_width"],
            {pos: [(200, -1.0), (201, -1.0), (202, -1.0)]},
        )
        uniform_parsed = self.client.parse_response(uniform_raw, compiled)
        self.assertAlmostEqual(
            uniform_parsed["answers"]["team"]["confidence"], 0.0, places=5
        )

        peaked_raw = _make_logprobs_response(
            compiled["canvas_width"],
            {pos: [(200, 0.0), (201, -100.0), (202, -100.0)]},
        )
        peaked_parsed = self.client.parse_response(peaked_raw, compiled)
        self.assertAlmostEqual(
            peaked_parsed["answers"]["team"]["confidence"], 1.0, places=5
        )

    def test_missing_label_token_defaults_to_floor(self) -> None:
        # Verify missing candidate token IDs default to -100.0 cleanly.
        schema = {
            "flag": {"type": "boolean", "instructions": "True or false?"}
        }
        compiled = self.client.build_canvas(schema)
        pos = compiled["slots"][0]["pos"]
        # Omit token 101 (false) from top_logprobs.
        raw = _make_logprobs_response(
            compiled["canvas_width"],
            {pos: [(100, 0.0)]},
        )
        parsed = self.client.parse_response(raw, compiled)
        self.assertAlmostEqual(
            parsed["answers"]["flag"]["boolean"], 1.0, places=5
        )


class TestResolveEndpoint(unittest.TestCase):
    """Tests endpoint lookup helper in diffusiongemma_client."""

    @mock.patch("diffusiongemma_client.aiplatform")
    def test_resolve_endpoint_by_display_name(
        self, mock_aiplatform: mock.MagicMock
    ) -> None:
        # Verify resolve_endpoint returns matching Endpoint from list().
        fake_ep = mock.MagicMock()
        mock_aiplatform.Endpoint.list.return_value = [fake_ep]
        self.assertIs(
            diffusiongemma_client.resolve_endpoint("diffusiongemma-vllm"),
            fake_ep,
        )


if __name__ == "__main__":
    unittest.main()
