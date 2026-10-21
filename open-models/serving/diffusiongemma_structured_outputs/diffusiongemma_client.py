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

"""Client and schema compiler for DiffusionGemma vLLM endpoints.

Implements single-pass masked-canvas classification (`choice`, `score`,
`boolean`) directly against an official `vllm/vllm-openai:v0.31.0` container
serving `nvidia/diffusiongemma-26B-A4B-it-NVFP4` on the Gemini platform
(`/v1/chat/completions`).
"""

import math
from typing import Any

from google.cloud import aiplatform
from transformers import AutoTokenizer

import config

# System instruction priming the model to output raw JSON without prose.
SYSTEM_PROMPT = (
    "Analyze the provided input and answer all requested questions."
    " Respond only with a valid JSON object matching the schema."
)


class DiffusionGemmaClient:
    """Builds masked-canvas requests and parses DiffusionGemma responses."""

    def __init__(
        self,
        tokenizer_id: str = config.HF_MODEL_ID,
        tokenizer: Any = None,
    ) -> None:
        self.tok = tokenizer or AutoTokenizer.from_pretrained(tokenizer_id)
        # Token ID 69 (<|Reserved_2|>) is DiffusionGemma's [MASK] placeholder.
        self.mask_id: int = self.tok.convert_tokens_to_ids("<|Reserved_2|>")
        self.pad_id: int = self.tok.pad_token_id or 0
        # Precompute single-token IDs for letters (A-Z), digits (0-9), and
        # booleans (true/false) so every answer fits in a 1-token mask slot.
        self.letter_ids: list[int] = [
            self._single_token_id(chr(ord("A") + i)) for i in range(26)
        ]
        self.digit_ids: list[int] = [
            self._single_token_id(str(d)) for d in range(10)
        ]
        self.true_id: int = self._single_token_id("true")
        self.false_id: int = self._single_token_id("false")

    def _single_token_id(self, text: str) -> int:
        ids = self.tok.encode(text, add_special_tokens=False)
        return ids[0]

    def _emit_tokens(self, canvas_ids: list[int], text: str) -> None:
        # Encode literal JSON syntax tokens and append them to the canvas.
        canvas_ids.extend(self.tok.encode(text, add_special_tokens=False))

    def _append_canvas_slot(
        self,
        canvas_ids: list[int],
        qid: str,
        quoted: bool,
        is_last: bool,
    ) -> int:
        # Append a JSON key and 1-token [MASK] slot to the canvas.
        prefix = f'"{qid}": "' if quoted else f'"{qid}": '
        self._emit_tokens(canvas_ids, prefix)
        pos = len(canvas_ids)
        canvas_ids.append(self.mask_id)
        if quoted:
            suffix = '"' if is_last else '", '
            self._emit_tokens(canvas_ids, suffix)
        elif not is_last:
            self._emit_tokens(canvas_ids, ", ")
        return pos

    def _compile_choice_question(
        self,
        qid: str,
        q_name: str,
        q_spec: dict[str, Any],
        canvas_ids: list[int],
        is_last: bool,
    ) -> tuple[str, dict[str, Any]]:
        # Map multi-token choice keys to single-token letters (A-Z).
        criteria = q_spec["criteria"]
        keys = list(criteria.keys())
        letters = [chr(ord("A") + j) for j in range(len(keys))]
        label_ids = self.letter_ids[: len(keys)]
        lines = [
            f"  {letters[j]} = {keys[j]}: {criteria[keys[j]]}"
            for j in range(len(keys))
        ]
        prompt_text = (
            f"[{qid}] ({q_name}) {q_spec['instructions']}\n"
            f"Answer with a single letter ({'/'.join(letters)}):\n"
            + "\n".join(lines)
            + "\n"
        )
        pos = self._append_canvas_slot(
            canvas_ids, qid, quoted=True, is_last=is_last
        )
        slot = {
            "name": q_name,
            "type": "choice",
            "pos": pos,
            "label_ids": label_ids,
            "keys": keys,
        }
        return prompt_text, slot

    def _compile_score_question(
        self,
        qid: str,
        q_name: str,
        q_spec: dict[str, Any],
        canvas_ids: list[int],
        is_last: bool,
    ) -> tuple[str, dict[str, Any]]:
        # Map ordinal rubric levels to single-digit tokens (0..N-1).
        criteria_list = q_spec["criteria"]
        n_levels = len(criteria_list)
        label_ids = self.digit_ids[:n_levels]
        legend = {str(j): criteria_list[j] for j in range(n_levels)}
        lines = [f"  {j} = {criteria_list[j]}" for j in range(n_levels)]
        prompt_text = (
            f"[{qid}] ({q_name}) {q_spec['instructions']}\n"
            f"Answer with a single digit (0-{n_levels - 1}):\n"
            + "\n".join(lines)
            + "\n"
        )
        pos = self._append_canvas_slot(
            canvas_ids, qid, quoted=False, is_last=is_last
        )
        slot = {
            "name": q_name,
            "type": "score",
            "pos": pos,
            "label_ids": label_ids,
            "legend": legend,
        }
        return prompt_text, slot

    def _compile_boolean_question(
        self,
        qid: str,
        q_name: str,
        q_spec: dict[str, Any],
        canvas_ids: list[int],
        is_last: bool,
    ) -> tuple[str, dict[str, Any]]:
        # Map binary questions to single-token 'true' and 'false' IDs.
        label_ids = [self.true_id, self.false_id]
        prompt_text = (
            f"[{qid}] ({q_name}) {q_spec['instructions']}\n"
            "Answer true or false.\n"
        )
        pos = self._append_canvas_slot(
            canvas_ids, qid, quoted=False, is_last=is_last
        )
        slot = {
            "name": q_name,
            "type": "boolean",
            "pos": pos,
            "label_ids": label_ids,
        }
        return prompt_text, slot

    def build_canvas(self, questions: dict[str, dict[str, Any]]) -> dict:
        # Build the user prompt rubric and the seeded JSON token canvas.
        prompt_parts: list[str] = ["### Questions\n"]
        canvas_ids: list[int] = []
        slots: list[dict[str, Any]] = []
        all_label_ids: set[int] = set()

        # Start the JSON object on the canvas.
        self._emit_tokens(canvas_ids, "{")
        items = list(questions.items())
        for idx, (q_name, q_spec) in enumerate(items):
            qid = f"q{idx}"
            q_type = q_spec["type"]
            is_last = idx + 1 == len(items)

            if q_type == "choice":
                prompt_text, slot = self._compile_choice_question(
                    qid, q_name, q_spec, canvas_ids, is_last
                )
            elif q_type == "score":
                prompt_text, slot = self._compile_score_question(
                    qid, q_name, q_spec, canvas_ids, is_last
                )
            elif q_type == "boolean":
                prompt_text, slot = self._compile_boolean_question(
                    qid, q_name, q_spec, canvas_ids, is_last
                )
            else:
                raise ValueError(f"Unsupported question type: {q_type!r}")

            prompt_parts.append(prompt_text)
            slots.append(slot)
            all_label_ids.update(slot["label_ids"])

        # Close the JSON object and pad the canvas to a multiple of 16 tokens.
        self._emit_tokens(canvas_ids, "}")
        template_len = len(canvas_ids)
        canvas_width = max(16, ((template_len + 15) // 16) * 16)
        seed_canvas = canvas_ids + [self.pad_id] * (canvas_width - template_len)
        return {
            "question_block": "\n".join(prompt_parts),
            "seed_canvas": seed_canvas,
            "canvas_width": canvas_width,
            "slots": slots,
            "all_label_ids": sorted(all_label_ids),
        }

    def build_request(
        self,
        state: str,
        compiled: dict[str, Any],
        model: str = config.SERVED_MODEL_NAME,
    ) -> dict[str, Any]:
        # Combine the input state and compiled rubric into a user prompt.
        user_msg = (
            f"### State\n{state}\n\n{compiled['question_block']}\n"
            "Fill in every field of the JSON object accurately."
        )
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": compiled["canvas_width"],
            "logprobs": True,
            "top_logprobs": len(compiled["all_label_ids"]),
            # Restrict logprobs to valid option IDs and return raw token IDs.
            "logprob_token_ids": compiled["all_label_ids"],
            "return_tokens_as_token_ids": True,
            "chat_template_kwargs": {"enable_thinking": False},
            # Configure 1-step read-only constrained diffusion over the canvas.
            "vllm_xargs": {
                "diffusion_seed_canvas": compiled["seed_canvas"],
                "diffusion_max_steps": 1,
                "diffusion_read_only": True,
                "diffusion_constrained": True,
                "diffusion_canvas_length": compiled["canvas_width"],
            },
        }

    def _compute_slot_probs_and_confidence(
        self,
        entry: dict[str, Any],
        label_ids: list[int],
    ) -> tuple[list[float], float]:
        # Parse token IDs from vLLM's 'token_id:<id>' string format.
        lp_map: dict[int, float] = {}
        for cand in entry.get("top_logprobs", []):
            tid = int(cand["token"].split(":")[-1])
            lp_map[tid] = float(cand["logprob"])

        # Softmax over the valid label token IDs for this question.
        raw_logprobs = [lp_map.get(t, -100.0) for t in label_ids]
        max_lp = max(raw_logprobs)
        exp_vals = [math.exp(lp - max_lp) for lp in raw_logprobs]
        total = sum(exp_vals) or 1.0
        probs = [e / total for e in exp_vals]

        # Compute normalized Shannon entropy confidence: 1 - H(p) / ln(K).
        k = len(probs)
        entropy = -sum(p * math.log(p) for p in probs if p > 0)
        conf = 1.0 - (entropy / math.log(k)) if k > 1 else 1.0
        return probs, conf

    def _format_slot_answer(
        self,
        slot: dict[str, Any],
        probs: list[float],
        conf: float,
    ) -> dict[str, Any]:
        # Format normalized slot probabilities into a typed answer dictionary.
        k = len(probs)
        if slot["type"] == "choice":
            # Map single-letter probabilities back to original choice keys.
            keys = slot["keys"]
            prob_dict = {keys[i]: round(probs[i], 6) for i in range(k)}
            best_idx = max(range(k), key=lambda i: probs[i])
            return {
                "type": "choice",
                "choice": keys[best_idx],
                "probabilities": prob_dict,
                "confidence": round(conf, 6),
            }
        if slot["type"] == "score":
            # Compute the probability-weighted expected score: sum(i * p_i).
            prob_dict = {str(i): round(probs[i], 6) for i in range(k)}
            expected = sum(i * probs[i] for i in range(k))
            return {
                "type": "score",
                "score": round(expected, 6),
                "legend": slot["legend"],
                "probabilities": prob_dict,
                "confidence": round(conf, 6),
            }
        # Return P(true) for binary boolean questions.
        return {
            "type": "boolean",
            "boolean": round(probs[0], 6),
        }

    def parse_response(
        self, raw_json: dict[str, Any], compiled: dict[str, Any]
    ) -> dict[str, Any]:
        # Extract log-probabilities at each mask slot and normalize answers.
        content = raw_json["choices"][0]["logprobs"]["content"]
        answers: dict[str, Any] = {}
        for slot in compiled["slots"]:
            entry = content[slot["pos"]]
            probs, conf = self._compute_slot_probs_and_confidence(
                entry, slot["label_ids"]
            )
            answers[slot["name"]] = self._format_slot_answer(slot, probs, conf)

        usage = raw_json.get("usage", {})
        return {
            "model": raw_json.get("model", config.SERVED_MODEL_NAME),
            "answers": answers,
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": 0,
            },
        }


def resolve_endpoint(name_or_id: str) -> aiplatform.Endpoint:
    """Resolves an Endpoint by display_name or resource ID."""
    endpoints = aiplatform.Endpoint.list(filter=f'display_name="{name_or_id}"')
    if endpoints:
        return endpoints[0]
    return aiplatform.Endpoint(name_or_id)
