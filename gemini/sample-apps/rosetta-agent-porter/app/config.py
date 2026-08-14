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
"""Central configuration + model factories for Rosetta.

The model ID, the per-role thinking levels and the pipeline caps all live here,
so the speed/quality tradeoff is tuned in one place.

Model policy: ONE model — Gemini 3.7 Flash — for every role. It does the parallel
repo read (framework detect, the 6-way analysis swarm, input harvesting) AND the
reasoning-heavy design steps (port plan, codegen, self-heal, eval authoring).
https://ai.google.dev/gemini-api/docs/models

The per-role knob is the THINKING BUDGET, not the model: high-volume reading runs
at LOW so the swarm stays fast, while the port planner and codegen think at
MEDIUM. See ROLE_THINKING.

Backends: works with either
  * the Gemini API (Google AI Studio) — set GOOGLE_API_KEY, or
  * Gemini Enterprise Agent Platform — set GOOGLE_CLOUD_PROJECT.
Rosetta picks whichever you configured; see `_resolve_backend()`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE importing the SDKs: google-genai reads its backend/auth
# settings from the environment at import time.
#
# Pinned to THIS project's .env. Bare load_dotenv() searches parent directories,
# so an unrelated .env further up someone's tree can silently configure the app
# (it found one two levels up during development and picked a different backend
# than the one requested).
#
# override=False on purpose: a variable you exported yourself beats .env, so
# `GOOGLE_CLOUD_PROJECT=my-proj make dev` does what it looks like it does. Keep
# defaults in .env; override them from the shell when you need to.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from google.adk.models import Gemini  # noqa: E402  (import after dotenv)
from google.genai import types  # noqa: E402

# --- Model ------------------------------------------------------------------
# The one model that runs the whole pipeline.
MODEL_ID = os.getenv("ROSETTA_MODEL", "gemini-3.7-flash")

# Public display name — the only model string the UI ever shows. The cockpit
# reads it from GET /api/config, so it is never hardcoded in the frontend.
MODEL_NAME = os.getenv("ROSETTA_MODEL_NAME", "Gemini 3.7 Flash")

# Aliases: the agent role table, the prompt sentinels, the PortPlan schema and
# every generated project speak 'smart'/'fast'. Both resolve to the same model.
# Kept as env-overridable escape hatches if you ever want to split the tiers.
MODEL_SMART = os.getenv("ROSETTA_MODEL_SMART", MODEL_ID)
MODEL_FAST = os.getenv("ROSETTA_MODEL_FAST", MODEL_ID)
MODEL_SMART_NAME = os.getenv("ROSETTA_MODEL_SMART_NAME", MODEL_NAME)
MODEL_FAST_NAME = os.getenv("ROSETTA_MODEL_FAST_NAME", MODEL_NAME)


# --- Backend: Gemini API (AI Studio) or Gemini Enterprise Agent Platform -----
def _resolve_backend() -> tuple[bool, str, str]:
    """Pick the Gemini backend from the environment.

    Returns (use_agent_platform, project, location).

    Precedence:
      1. ROSETTA_BACKEND, if set: "agent-platform" or "ai-studio".
      2. GOOGLE_API_KEY / GEMINI_API_KEY present -> Gemini API (AI Studio).
      3. GOOGLE_CLOUD_PROJECT present            -> Gemini Enterprise Agent Platform.
    Raises with actionable instructions when nothing is configured, because the
    alternative is a stack trace from deep inside the SDK on the first call.

    The resolved choice is written back to os.environ so the ADK/genai clients —
    and the `adk api_server` child process Rosetta launches for a ported agent —
    all agree on one backend.
    """
    choice = (os.getenv("ROSETTA_BACKEND") or "").strip().lower()
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

    if choice in ("agent-platform", "agent_platform", "platform"):
        use_agent_platform = True
    elif choice in ("ai-studio", "ai_studio", "studio", "api"):
        use_agent_platform = False
    elif choice:
        raise RuntimeError(
            f"ROSETTA_BACKEND={choice!r} is not valid. "
            'Use "agent-platform" or "ai-studio".'
        )
    elif api_key:
        use_agent_platform = False
    elif project:
        use_agent_platform = True
    else:
        raise RuntimeError(
            "No Gemini backend configured. Pick one and re-run:\n"
            "  * Gemini API (Google AI Studio) — fastest to start:\n"
            "      export GOOGLE_API_KEY=...      # https://aistudio.google.com/apikey\n"
            "  * Gemini Enterprise Agent Platform:\n"
            "      gcloud auth application-default login\n"
            "      export GOOGLE_CLOUD_PROJECT=your-project-id\n"
            "Or copy .env.example to .env and fill in one of them."
        )

    if use_agent_platform and not project:
        raise RuntimeError(
            "Gemini Enterprise Agent Platform selected but GOOGLE_CLOUD_PROJECT is "
            "not set.\n  export GOOGLE_CLOUD_PROJECT=your-project-id\n"
            "and make sure credentials are available: "
            "gcloud auth application-default login"
        )
    if not use_agent_platform and not api_key:
        raise RuntimeError(
            "Gemini API backend selected but no GOOGLE_API_KEY / GEMINI_API_KEY is set.\n"
            "Create one at https://aistudio.google.com/apikey"
        )

    # The google-genai SDK selects its backend from this variable; the name is the
    # library's, not ours, so it is set here and never surfaced to the user.
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true" if use_agent_platform else "false"
    if use_agent_platform:
        os.environ["GOOGLE_CLOUD_LOCATION"] = location
    return use_agent_platform, project, location


USE_AGENT_PLATFORM, PROJECT_ID, LOCATION = _resolve_backend()

# Human-readable backend label — shown in the cockpit and in generated projects.
BACKEND_NAME = (
    "Gemini Enterprise Agent Platform"
    if USE_AGENT_PLATFORM
    else "Gemini API (AI Studio)"
)

# --- Pipeline caps (tunable knobs) ------------------------------------------
# Rosetta is quality-first, not latency-first: caps are generous.
MAX_SOURCE_FILES = int(
    os.getenv("ROSETTA_MAX_SOURCE_FILES", "40")
)  # files the swarm may read
MAX_FILE_CHARS = int(
    os.getenv("ROSETTA_MAX_FILE_CHARS", "24000")
)  # per-file injection cap
MAX_SOURCE_BLOCK_CHARS = int(
    os.getenv("ROSETTA_MAX_SOURCE_BLOCK", "120000")
)  # per-facet cap
MAX_REPAIRS = int(os.getenv("ROSETTA_MAX_REPAIRS", "3"))  # self-heal passes
MAX_EVAL_CASES = int(os.getenv("ROSETTA_MAX_EVAL_CASES", "6"))  # fidelity dataset size
CODEGEN_MAX_TOKENS = int(os.getenv("ROSETTA_CODEGEN_MAX_TOKENS", "32000"))
PLAN_MAX_TOKENS = int(os.getenv("ROSETTA_PLAN_MAX_TOKENS", "16000"))

# Which model each role runs on. Keep this table the single source of truth.
SMART = "smart"
FAST = "fast"
ROLE_MODEL = {
    "intake": FAST,  # framework detect + file triage (classification/routing)
    "graph_analyst": FAST,  # control-flow extraction (LOW thinking — most reasoning-heavy analyst)
    "prompt_analyst": FAST,
    "tool_analyst": FAST,
    "state_analyst": FAST,
    "model_analyst": FAST,
    "input_harvester": FAST,  # mine example inputs from the repo
    "symbol_researcher": FAST,  # google_search unknown framework symbols
    "port_planner": SMART,  # THE mapping IR — the intelligence highlight
    "codegen": SMART,  # generate the ADK project
    "fixer": SMART,  # minimal-diff self-heal
    "eval_author": SMART,  # eval dataset + fidelity rubric
}

_TL = types.ThinkingLevel
# Per-role thinking budget. FAST roles stay cheap; SMART design roles get more.
# LOW is the FLOOR here, not a preference. ThinkingLevel.MINIMAL is rejected by
# this model:
#   400 INVALID_ARGUMENT: Thinking level is unsupported: THINKING_LEVEL_MINIMAL
# and it fails the whole pipeline on the very first swarm call rather than
# degrading. If you lower these, re-check that the level is still accepted.
ROLE_THINKING = {
    "intake": _TL.LOW,
    "graph_analyst": _TL.LOW,  # control flow drives the mapping
    "prompt_analyst": _TL.LOW,
    "tool_analyst": _TL.LOW,
    "state_analyst": _TL.LOW,  # reducer semantics are subtle
    "model_analyst": _TL.LOW,
    "input_harvester": _TL.LOW,
    "symbol_researcher": _TL.LOW,
    "port_planner": _TL.MEDIUM,  # the crux — can raise to HIGH if quality demands
    "codegen": _TL.MEDIUM,
    "fixer": _TL.LOW,
    "eval_author": _TL.LOW,
}


def model_id(role: str) -> str:
    return MODEL_SMART if ROLE_MODEL.get(role, SMART) == SMART else MODEL_FAST


def make_model(role_or_id: str) -> Gemini:
    """ADK Gemini wrapper (with retry for transient 429s under swarm fan-out).

    Accepts a role name (looked up in ROLE_MODEL) or a raw model id.
    """
    mid = model_id(role_or_id) if role_or_id in ROLE_MODEL else role_or_id
    return Gemini(model=mid, retry_options=types.HttpRetryOptions(attempts=3))


def gen_config(
    role: str,
    *,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> types.GenerateContentConfig:
    """GenerateContentConfig carrying the role's thinking level."""
    kwargs: dict = {
        "thinking_config": types.ThinkingConfig(
            thinking_level=ROLE_THINKING.get(role, _TL.LOW)
        ),
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = max_output_tokens
    return types.GenerateContentConfig(**kwargs)
