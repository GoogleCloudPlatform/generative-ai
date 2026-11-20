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

# ruff: noqa: INP001, S101, PLR2004

"""AgentOps Gate 1, Gate 2 & Gate 3 test suite for the FinOps Advisor Agent.

Covers deterministic fast checks (`< 0.2s` on CPU, zero cloud credentials
needed) alongside an opt-in live ADK `AgentEvaluator` integration test:

- Gate 1 / Gate 2 (local pre-commit & GitHub PR CI):
    PYTHONPATH=. pytest tests/unit/test_agent_unit.py -k "not integration" -v
- Gate 3A (opt-in live ADK evaluation via pytest):
    RUN_LIVE_ADK_EVAL=1 PYTHONPATH=. pytest tests/unit/test_agent_unit.py
"""

from __future__ import annotations

import json
import os
import pathlib
import re

import tomllib  # isort: skip

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from app.agent import (
    DEFAULT_LOCAL_MODEL_ID,
    DEFAULT_MAAS_MODEL_ID,
    GemmaEndpointLlm,
    assign_ab_variant,
    calculate_serving_cost,
    estimate_gemma_vram,
    get_environment_data_tier,
    get_gemma_model,
    root_agent,
    sanitize_trace_for_golden_evalset,
    size_endpoint_capacity,
)
from app.tool_parser import extract_tool_calls_from_text

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Gate 1 & 2: Deterministic Unit Tests (FinOps Tools, MaaS Routing, A/B)
# ---------------------------------------------------------------------------
def test_estimate_gemma_vram_26b_moe() -> None:
    """Verifies 4-bit weight + KV-cache memory math and hardware tier mapping."""
    res = estimate_gemma_vram("gemma-4-26B-A4B-it", "4bit")
    assert res["weights_memory_gb"] == pytest.approx(14.3)
    assert res["kv_cache_headroom_gb"] == pytest.approx(6.5)
    assert res["total_recommended_vram_gb"] == pytest.approx(20.8)
    assert "24GB" in res["dev_mac_recommendation"]


def test_calculate_serving_cost_hibernation_savings() -> None:
    """Verifies active monthly GPU spend vs. 24x7 spend and hibernation delta."""
    res = calculate_serving_cost(
        platform="gemini_agent_platform",
        gpu_type="nvidia-l4",
        hours_per_day=10.0,
        replicas=2,
    )
    assert res["monthly_cost_usd"] == pytest.approx(690.0)
    assert res["full_time_24x7_cost_usd"] == pytest.approx(1656.0)
    assert res["monthly_hibernation_savings_usd"] == pytest.approx(966.0)


def test_size_endpoint_capacity_from_staging_baseline() -> None:
    """Verifies replica sizing from single-GPU baseline throughput (`4.5 RPCs/s`)."""
    res = size_endpoint_capacity(
        concurrent_users=150,
        turns_per_request=2,
        target_p95_seconds=30.0,
        measured_rpcs_per_sec_per_gpu=4.5,
    )
    assert res["total_predict_rpcs_per_burst"] == 300
    assert res["max_users_per_single_gpu_replica"] == 67
    assert res["recommended_gpu_min_replicas"] == 3
    assert res["recommended_cloud_run_min_instances"] == 3


def test_size_endpoint_capacity_handles_non_positive_args() -> None:
    """Guards against LLMs passing 0 or negative defaults for omitted optional args."""
    res = size_endpoint_capacity(
        concurrent_users=150,
        turns_per_request=0,
        target_p95_seconds=0.0,
        measured_rpcs_per_sec_per_gpu=-1.0,
    )
    assert res["turns_per_request"] == 2
    assert res["measured_rpcs_per_sec_per_gpu"] == pytest.approx(4.5)
    assert res["recommended_gpu_min_replicas"] == 3
    assert res["recommended_cloud_run_min_instances"] == 3


def test_get_gemma_model_routing_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies dynamic dev/staging/prod routing without module reload."""
    monkeypatch.delenv("USE_MAAS", raising=False)
    monkeypatch.delenv("GEMMA_MAAS_MODEL_ID", raising=False)
    monkeypatch.delenv("GEMMA_MODEL_ID", raising=False)
    monkeypatch.delenv("GEMMA_SERVER_URL", raising=False)

    monkeypatch.setenv("AGENT_ENV", "dev")
    dev_model = get_gemma_model()
    assert dev_model.use_maas is False
    assert dev_model.model == DEFAULT_LOCAL_MODEL_ID
    assert dev_model.api_base == "http://127.0.0.1:8080/v1"

    for env_name in ("staging", "prod"):
        monkeypatch.setenv("AGENT_ENV", env_name)
        cloud_model = get_gemma_model()
        assert cloud_model.use_maas is True
        assert cloud_model.model == DEFAULT_MAAS_MODEL_ID

    monkeypatch.setenv("AGENT_ENV", "dev")
    monkeypatch.setenv("USE_MAAS", "1")
    monkeypatch.setenv("GEMMA_MAAS_MODEL_ID", "google/gemma-4-custom-maas")
    override_model = get_gemma_model()
    assert override_model.use_maas is True
    assert override_model.model == "google/gemma-4-custom-maas"


def test_maas_request_conversion_preserves_tool_turns() -> None:
    """Verifies OpenAI native `system`/`assistant tool_calls`/`tool` wire shapes."""
    llm = GemmaEndpointLlm(model=DEFAULT_MAAS_MODEL_ID, use_maas=True)
    req = LlmRequest(
        contents=[
            types.Content(role="user", parts=[types.Part.from_text(text="Size 26B?")]),
            types.Content(
                role="model",
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id="call_1",
                            name="estimate_gemma_vram",
                            args={"model_variant": "gemma-4-26B-A4B-it"},
                        )
                    )
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id="call_1",
                            name="estimate_gemma_vram",
                            response={"total_recommended_vram_gb": 20.8},
                        )
                    )
                ],
            ),
        ],
        config=types.GenerateContentConfig(
            system_instruction="Be concise.",
            tools=[
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name="estimate_gemma_vram",
                            description="Estimate VRAM",
                            parameters=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "model_variant": types.Schema(
                                        type=types.Type.STRING
                                    )
                                },
                            ),
                        )
                    ]
                )
            ],
        ),
    )

    # pylint: disable=protected-access
    messages, tools = llm._convert_llm_request_maas(req)  # noqa: SLF001
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "tool"]
    assert messages[2]["tool_calls"][0]["function"]["name"] == "estimate_gemma_vram"
    assert messages[3]["tool_call_id"] == "call_1"
    assert json.loads(messages[3]["content"])["total_recommended_vram_gb"] == 20.8
    assert tools[0]["function"]["parameters"]["type"] == "object"
    assert (
        tools[0]["function"]["parameters"]["properties"]["model_variant"]["type"]
        == "string"
    )


def test_sticky_ab_bucketing_is_deterministic() -> None:
    """Verifies SHA-256 user-ID bucketing stays sticky across multi-turn calls."""
    user_a = "finops-user-42"
    first_call = assign_ab_variant(user_a, treatment_pct=20)
    for _ in range(50):
        assert assign_ab_variant(user_a, treatment_pct=20) == first_call

    for uid in ["user-1", "user-2", "user-3", "alice@example.com", "bob-99"]:
        assert assign_ab_variant(uid, treatment_pct=0) == "A"
        assert assign_ab_variant(uid, treatment_pct=100) == "B"


def test_supply_chain_native_adk_base_llm_and_allowlisted_deps() -> None:
    """Verifies `GemmaEndpointLlm` inheritance and strict runtime package allowlist."""
    assert isinstance(root_agent.model, BaseLlm)
    assert isinstance(root_agent.model, GemmaEndpointLlm)

    pyproject_data = tomllib.loads(
        (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    allowed = {"google-adk", "google-auth", "httpx", "python-dotenv"}
    for dep in pyproject_data["project"]["dependencies"]:
        pkg_name = re.split(r"[><=~!;\[]", dep)[0].strip().lower().replace("_", "-")
        assert pkg_name in allowed, (
            f"Unapproved runtime dependency in pyproject.toml: '{dep}'"
        )


def test_text_tool_call_extraction() -> None:
    """Verifies shared AST and JSON fallback tool-call extraction."""
    tools_payload = [
        {
            "type": "function",
            "function": {
                "name": "estimate_gemma_vram",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "quantization": {"type": "string"},
                    },
                },
            },
        }
    ]

    sample_code = (
        "```tool_code\n"
        'print(estimate_gemma_vram(model="gemma-4-26B-A4B-it", quantization="4bit"))\n'
        "```"
    )
    cleaned, calls = extract_tool_calls_from_text(sample_code, tools_payload)
    assert cleaned == ""
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "estimate_gemma_vram"
    assert json.loads(calls[0]["function"]["arguments"]) == {
        "model": "gemma-4-26B-A4B-it",
        "quantization": "4bit",
    }

    sample_json = (
        "```json\n"
        '{"tool_call": {"name": "estimate_gemma_vram", "arguments": {"model": "gemma-4-12b-it"}}}\n'
        "```"
    )
    cleaned_j, calls_j = extract_tool_calls_from_text(sample_json, tools_payload)
    assert cleaned_j == ""
    assert len(calls_j) == 1
    assert json.loads(calls_j[0]["function"]["arguments"]) == {
        "model": "gemma-4-12b-it"
    }

    sample_text = "The VRAM requirement for this model is approximately 16.5 GB."
    cleaned_t, calls_t = extract_tool_calls_from_text(sample_text, tools_payload)
    assert cleaned_t == sample_text
    assert calls_t == []


def test_data_governance_tier_and_trace_pii_sanitization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies per-environment data tiers and redaction of PII/credentials."""
    monkeypatch.delenv("DATA_GOVERNANCE_TIER", raising=False)
    assert get_environment_data_tier("dev") == "synthetic_fixtures_only"
    assert get_environment_data_tier("staging") == "anonymized_staging_snapshot"
    assert get_environment_data_tier("prod") == "live_production_data"

    fake_oauth = "ya29." + "a0AfH6SMB_dummy_fixture"
    fake_api_key = "AIza" + "SyD9uG1L5x0M2p3Q4r5S6t7U8v9W0x1Y2z0"
    raw_trace = (
        "User alice.finops@example.com asked about billing account"
        f" 01A2B3-4C5D6E-7F8A9B using Bearer {fake_oauth}"
        f" and API key {fake_api_key}"
    )
    sanitized = sanitize_trace_for_golden_evalset(raw_trace)
    for secret in (
        "alice.finops@example.com",
        "01A2B3-4C5D6E-7F8A9B",
        fake_oauth,
        fake_api_key,
    ):
        assert secret not in sanitized
    assert "<REDACTED_EMAIL>" in sanitized
    assert "<REDACTED_BILLING_ACCOUNT>" in sanitized
    assert "Bearer <REDACTED_TOKEN>" in sanitized
    assert "<REDACTED_API_KEY>" in sanitized


def test_stage1_golden_work_multiplier_budget() -> None:
    """Verifies every golden evalset case stays within `K <= 2` LLM turns."""
    evalset_path = _REPO_ROOT / "tests" / "eval" / "evalsets" / "golden.evalset.json"
    eval_cases = json.loads(evalset_path.read_text(encoding="utf-8")).get(
        "eval_cases", []
    )
    assert len(eval_cases) >= 3

    for case in eval_cases:
        eval_id = case["eval_id"]
        tool_uses = (
            case["conversation"][0].get("intermediate_data", {}).get("tool_uses", [])
        )
        tool_count = len(tool_uses)
        work_multiplier_k = 1 + tool_count
        assert tool_count == 1, f"{eval_id} expected 1 tool call, got {tool_count}"
        assert work_multiplier_k <= 2, (
            f"{eval_id} exceeded K=2 LLM turns ({work_multiplier_k})"
        )


# ---------------------------------------------------------------------------
# Gate 3: Live ADK AgentEvaluator Trajectory & LLM-as-a-Judge Gate
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_ADK_EVAL") != "1",
    reason="Set RUN_LIVE_ADK_EVAL=1 to execute live ADK evaluation against Gemma 4.",
)
async def test_integration_adk_golden_evalset() -> None:
    """Executes ADK `AgentEvaluator` end-to-end when `RUN_LIVE_ADK_EVAL=1`."""
    # pylint: disable=import-outside-toplevel
    from google.adk.evaluation.agent_evaluator import AgentEvaluator  # noqa: PLC0415

    evalset_path = _REPO_ROOT / "tests" / "eval" / "evalsets" / "golden.evalset.json"
    await AgentEvaluator.evaluate(
        agent_module="app",
        eval_dataset_file_path_or_dir=str(evalset_path),
        num_runs=1,
    )
