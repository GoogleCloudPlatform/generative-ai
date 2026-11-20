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

"""Cloud FinOps & GPU Capacity Advisor Agent (`app/agent.py`).

Environment promotion across all three AgentOps stages is controlled purely via
environment configuration (zero code changes between stages):
- `AGENT_ENV=dev` (default): Connects to the warm local Apple Silicon server
  (`model_serving/gemma_server.py`) via `/v1/chat/completions`.
- `AGENT_ENV=staging`: Connects from Cloud Run Staging to serverless Gemini Agent Platform
  Gemma 4 MaaS (`google/gemma-4-26b-a4b-it-maas`, `global`, `$0` idle cost).
- `AGENT_ENV=prod`: Connects from Cloud Run Production to serverless Gemini Agent Platform
  Gemma 4 MaaS (`global`), scaling smoothly with Provisioned Throughput (PT).
"""

import argparse
import asyncio
import hashlib
import math
import os
import re
from typing import Any

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.runners import InMemoryRunner
from google.genai import types

from app.gemma_llm import GemmaEndpointLlm, resolve_project_id
from app.tool_parser import extract_tool_calls_from_text

load_dotenv()

AGENT_ENV = os.environ.get("AGENT_ENV", "dev").lower()
DEFAULT_LOCAL_URL = "http://127.0.0.1:8080/v1"
DEFAULT_LOCAL_MODEL_ID = "mlx-community/gemma-3-12b-it-4bit"
DEFAULT_MAAS_MODEL_ID = "google/gemma-4-26b-a4b-it-maas"

if AGENT_ENV in ("staging", "prod"):
    # Ensure ADK evaluation judges (Gemini 3.8 Flash) authenticate via Gemini Agent Platform IAM.
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")

_PROJECT_ID = resolve_project_id()
if _PROJECT_ID:
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", _PROJECT_ID)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

_DATA_TIER_BY_ENV = {
    "dev": "synthetic_fixtures_only",
    "staging": "anonymized_staging_snapshot",
    "prod": "live_production_data",
}

# Re-export symbols consumed by callers and unit tests.
_extract_tool_calls_from_text = extract_tool_calls_from_text


def get_gemma_model() -> GemmaEndpointLlm:
    """Returns a `GemmaEndpointLlm` configured for the active `AGENT_ENV`.

    - `staging` / `prod` (or `USE_MAAS=1`): Serverless Gemini Agent Platform Gemma 4
      MaaS (`google/gemma-4-26b-a4b-it-maas` on `global`).
    - `dev` (default): Local Apple Silicon server (`GEMMA_SERVER_URL`).
    """
    active_env = os.environ.get("AGENT_ENV", AGENT_ENV).lower()
    if os.environ.get("USE_MAAS") == "1" or active_env in ("staging", "prod"):
        return GemmaEndpointLlm(
            model=os.environ.get("GEMMA_MAAS_MODEL_ID") or DEFAULT_MAAS_MODEL_ID,
            use_maas=True,
        )
    return GemmaEndpointLlm(
        model=os.environ.get("GEMMA_MODEL_ID") or DEFAULT_LOCAL_MODEL_ID,
        api_base=os.environ.get("GEMMA_SERVER_URL") or DEFAULT_LOCAL_URL,
    )


def assign_ab_variant(user_id: str, treatment_pct: int = 10) -> str:
    """Assigns a deterministic sticky-session A/B bucket (`'A'` or `'B'`)."""
    bucket = int(hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "B" if bucket < treatment_pct else "A"


_VRAM_TIER_SMALL_GB = 8.0
_VRAM_TIER_MEDIUM_GB = 22.0
_VRAM_TIER_LARGE_GB = 38.0


def _parse_positive_int(raw: Any, default: int) -> int:
    """Parses a strictly positive integer, returning `default` for <= 0/invalid."""
    try:
        val = int(raw)
    except (ValueError, TypeError):
        return default
    return val if val > 0 else default


def _parse_positive_float(raw: Any, default: float, minimum: float) -> float:
    """Parses a strictly positive float clamped at `minimum`, or `default`."""
    try:
        val = float(raw)
    except (ValueError, TypeError):
        return default
    return max(minimum, val) if val > 0 else default


# ---------------------------------------------------------------------------
# Cloud FinOps & GPU Capacity Advisor Tools
# ---------------------------------------------------------------------------
def estimate_gemma_vram(
    model_variant: str, quantization: str = "4bit"
) -> dict[str, Any]:
    """Estimates VRAM requirements and hardware tiers for a Gemma model variant.

    Args:
      model_variant: Gemma model name (e.g. 'gemma-4-12b-it', 'gemma-4-26B-A4B-it',
        'gemma-4-31B-it', 'gemma-4-E4B-it').
      quantization: Weight precision ('4bit', '8bit', or 'bfloat16').

    Returns:
      Dictionary containing weight memory, KV-cache headroom, total recommended
      VRAM in GB, and hardware tier recommendations for local Mac and Cloud GPUs.
    """
    param_map_gb = {
        "gemma-4-e2b-it": 2.3,
        "gemma-4-e4b-it": 4.5,
        "gemma-4-12b-it": 12.0,
        "gemma-4-26b-a4b-it": 26.0,
        "gemma-4-31b-it": 31.0,
        "gemma-3-4b-it": 4.0,
        "gemma-3-12b-it": 12.0,
        "gemma-3-27b-it": 27.0,
    }
    key = model_variant.strip().lower()
    params_b = param_map_gb.get(key)
    if params_b is None:
        match = re.search(r"(\d+)b", key)
        params_b = float(match.group(1)) if match else 12.0

    # Effective bytes per parameter including quantization metadata overhead.
    bytes_per_param = {
        "4bit": 0.55,
        "8bit": 1.05,
        "bfloat16": 2.0,
        "fp16": 2.0,
    }.get(quantization.strip().lower(), 0.55)

    weights_gb = round(params_b * bytes_per_param, 1)
    kv_cache_gb = round(max(2.0, params_b * 0.25), 1)
    total_vram_gb = round(weights_gb + kv_cache_gb, 1)

    if total_vram_gb <= _VRAM_TIER_SMALL_GB:
        mac_tier = "Mac M2/M3/M4 with 8GB-16GB Unified Memory (MLX)"
        cloud_gpu = "1x NVIDIA L4 (24 GB VRAM)"
    elif total_vram_gb <= _VRAM_TIER_MEDIUM_GB:
        mac_tier = "Mac M2/M3/M4 with 24GB-36GB Unified Memory (MLX)"
        cloud_gpu = "1x NVIDIA L4 (24 GB VRAM)"
    elif total_vram_gb <= _VRAM_TIER_LARGE_GB:
        mac_tier = "Mac M2/M3/M4 Max with 36GB-64GB Unified Memory"
        cloud_gpu = "1x NVIDIA A100 (40 GB VRAM) or 2x NVIDIA L4"
    else:
        mac_tier = "Mac M2/M3/M4 Ultra with 64GB-128GB Unified Memory"
        cloud_gpu = "1x NVIDIA A100 (80 GB) or H100 (80 GB)"

    return {
        "model_variant": model_variant,
        "quantization": quantization,
        "weights_memory_gb": weights_gb,
        "kv_cache_headroom_gb": kv_cache_gb,
        "total_recommended_vram_gb": total_vram_gb,
        "dev_mac_recommendation": mac_tier,
        "staging_and_prod_gpu_recommendation": cloud_gpu,
    }


def calculate_serving_cost(
    platform: str,
    gpu_type: str = "nvidia-l4",
    hours_per_day: float = 24.0,
    replicas: int = 1,
) -> dict[str, Any]:
    """Calculates monthly GPU serving cost and off-hours hibernation savings.

    Args:
      platform: Hosting platform ('mac_dev', 'cloud_run_staging', or 'gemini_agent_platform').
      gpu_type: GPU accelerator type ('nvidia-l4', 'nvidia-a100-40gb', 'nvidia-h100-80gb').
      hours_per_day: Active serving hours per day (1 to 24).
      replicas: Number of active GPU replicas.

    Returns:
      Dictionary containing hourly unit rate, active 30-day cost, 24x7 baseline
      cost, and monthly dollar savings from off-hours GPU hibernation.
    """
    hourly_rates = {
        "nvidia-l4": 1.15,
        "nvidia-a100-40gb": 3.67,
        "nvidia-a100-80gb": 4.95,
        "nvidia-h100-80gb": 10.80,
    }
    if platform.strip().lower() == "mac_dev":
        return {
            "platform": "mac_dev",
            "gpu_type": "apple-silicon-unified-memory",
            "hourly_rate_usd": 0.0,
            "monthly_cost_usd": 0.0,
            "full_time_24x7_cost_usd": 0.0,
            "monthly_hibernation_savings_usd": 0.0,
        }

    unit_rate = hourly_rates.get(gpu_type.strip().lower(), 1.15)
    try:
        active_hours = max(0.0, min(24.0, float(hours_per_day)))
    except (ValueError, TypeError):
        active_hours = 24.0
    try:
        reps = max(1, int(replicas))
    except (ValueError, TypeError):
        reps = 1

    monthly_active_cost = round(unit_rate * reps * active_hours * 30.0, 2)
    full_24x7_cost = round(unit_rate * reps * 24.0 * 30.0, 2)
    return {
        "platform": platform,
        "gpu_type": gpu_type,
        "replicas": reps,
        "hours_per_day": active_hours,
        "hourly_rate_per_replica_usd": unit_rate,
        "monthly_cost_usd": monthly_active_cost,
        "full_time_24x7_cost_usd": full_24x7_cost,
        "monthly_hibernation_savings_usd": round(
            full_24x7_cost - monthly_active_cost, 2
        ),
    }


def size_endpoint_capacity(
    concurrent_users: int,
    turns_per_request: int = 2,
    target_p95_seconds: float = 30.0,
    measured_rpcs_per_sec_per_gpu: float = 4.5,
) -> dict[str, Any]:
    """Sizes GPU replicas and Cloud Run instances for a target concurrency burst.

    Args:
      concurrent_users: Target peak simultaneous users in a burst (e.g. 50, 100, 250).
      turns_per_request: Number of sequential LLM RPCs per user turn (2 for single-tool calls).
      target_p95_seconds: Maximum acceptable end-to-end P95 latency in seconds.
      measured_rpcs_per_sec_per_gpu: Single-GPU baseline throughput in RPCs/sec
        (defaults to 4.5 RPCs/s).

    Returns:
      Dictionary with total burst RPCs, required RPCs/sec, max users per single
      GPU replica, and recommended min/max GPU replicas and Cloud Run instances.
    """
    # Treat non-positive values as omitted optional arguments so LLMs passing `0`
    # fall back to documented defaults instead of clamping `target_p95_seconds` low.
    users = _parse_positive_int(concurrent_users, 100)
    turns = _parse_positive_int(turns_per_request, 2)
    p95_slo = _parse_positive_float(target_p95_seconds, 30.0, minimum=5.0)
    gpu_unit_rps = _parse_positive_float(
        measured_rpcs_per_sec_per_gpu, 4.5, minimum=0.5
    )

    total_llm_rpcs = users * turns
    required_rps = round(total_llm_rpcs / p95_slo, 2)
    max_users_per_gpu_replica = max(1, int((gpu_unit_rps * p95_slo) // turns))
    recommended_gpu_replicas = max(1, math.ceil(required_rps / gpu_unit_rps))
    recommended_cloud_run_instances = max(1, math.ceil(users / 60.0))

    return {
        "concurrent_users": users,
        "turns_per_request": turns,
        "total_predict_rpcs_per_burst": total_llm_rpcs,
        "required_rpcs_per_sec": required_rps,
        "measured_rpcs_per_sec_per_gpu": gpu_unit_rps,
        "max_users_per_single_gpu_replica": max_users_per_gpu_replica,
        "recommended_gpu_min_replicas": recommended_gpu_replicas,
        "recommended_gpu_max_replicas": recommended_gpu_replicas + 2,
        "recommended_cloud_run_min_instances": recommended_cloud_run_instances,
        "recommendation": (
            f"{recommended_gpu_replicas}-{recommended_gpu_replicas + 2} GPU"
            f" replicas and {recommended_cloud_run_instances} Cloud Run"
            " instances are recommended."
        ),
    }


# ---------------------------------------------------------------------------
# Environment Data Governance & PII Trace Sanitization Gate
# ---------------------------------------------------------------------------
def get_environment_data_tier(env_name: str | None = None) -> str:
    """Returns the data governance tier enforced for `dev`, `staging`, or `prod`."""
    explicit_tier = os.environ.get("DATA_GOVERNANCE_TIER")
    if explicit_tier:
        return explicit_tier
    active_env = (env_name or os.environ.get("AGENT_ENV", "dev")).lower()
    return _DATA_TIER_BY_ENV.get(active_env, "synthetic_fixtures_only")


def sanitize_trace_for_golden_evalset(raw_text: str) -> str:
    """Redacts PII and credentials before exporting traces to `golden.evalset.json`."""
    patterns = (
        (r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "<REDACTED_EMAIL>", 0),
        (
            r"\b[0-9A-F]{6}-[0-9A-F]{6}-[0-9A-F]{6}\b",
            "<REDACTED_BILLING_ACCOUNT>",
            re.IGNORECASE,
        ),
        (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer <REDACTED_TOKEN>", 0),
        (r"AIza[0-9A-Za-z\-_]{35}", "<REDACTED_API_KEY>", 0),
    )
    text = raw_text
    for pattern, repl, flags in patterns:
        text = re.sub(pattern, repl, text, flags=flags)
    return text


# ---------------------------------------------------------------------------
# ADK Root Agent & App Entrypoints
# ---------------------------------------------------------------------------
root_agent = Agent(
    name="finops_gemma_advisor",
    model=get_gemma_model(),
    description=(
        "Cloud FinOps & GPU Capacity Advisor powered by Gemma 4 and Google ADK."
    ),
    instruction=(
        "You are a Cloud FinOps and GPU Capacity Advisor powered by Gemma 4 and"
        " Google ADK. Always call `estimate_gemma_vram` when asked about VRAM"
        " or hardware sizing for a Gemma model, `calculate_serving_cost` when"
        " asked about monthly GPU serving costs or off-hours hibernation"
        " savings, and `size_endpoint_capacity` when asked how many GPU"
        " replicas or Cloud Run instances are needed for concurrent users."
        " Report the exact numbers returned by your tools concisely."
    ),
    tools=[
        estimate_gemma_vram,
        calculate_serving_cost,
        size_endpoint_capacity,
    ],
)

app = App(root_agent=root_agent, name="app")


async def run_chat(single_prompt: str | None = None) -> None:
    """Runs a single-turn in-memory ADK session and streams the final reply."""
    prompt = single_prompt or "How much VRAM does gemma-4-26B-A4B-it in 4bit need?"
    app_name, user_id, session_id = "finops_gemma_app", "finops_engineer", "session_1"

    runner = InMemoryRunner(agent=root_agent, app_name=app_name)
    await runner.session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    print(f"\nPrompt: {prompt}\nFinOps Gemma Advisor: ", end="", flush=True)
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=msg
    ):
        for part in (
            event.content.parts if event.content and event.content.parts else []
        ):
            if getattr(part, "function_call", None):
                fc = part.function_call
                print(
                    f"\n  [Calling tool: {fc.name}({dict(fc.args or {})})]",
                    flush=True,
                )
            elif getattr(part, "text", None) and event.is_final_response():
                print(part.text, end="", flush=True)
    print()


def main() -> None:
    """Parses `--prompt` CLI argument and executes `run_chat()`."""
    parser = argparse.ArgumentParser(
        description="Cloud FinOps & GPU Capacity Advisor Agent (Google ADK + Gemma 4)."
    )
    parser.add_argument("--prompt", default=None, help="Run a single prompt and exit.")
    asyncio.run(run_chat(single_prompt=parser.parse_args().prompt))


if __name__ == "__main__":
    main()
