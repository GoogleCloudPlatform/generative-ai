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
"""Central configuration + model factories for Prism.

Every model ID, thinking level and latency knob lives here, so the
speed/quality tradeoff is tuned in one place.

Model policy: ONE model — Gemini 3.7 Flash — for every role. The gatekeeper,
the planner, all five parallel grounded-research workers and every UI generator
are the same model. There is deliberately no cheaper second tier.
https://ai.google.dev/gemini-api/docs/models

The per-role knob is the THINKING LEVEL, not the model. See THINK / MODES.

Backends: works with either
  * the Gemini API (Google AI Studio) — set GOOGLE_API_KEY, or
  * Gemini Enterprise Agent Platform — set GOOGLE_CLOUD_PROJECT.
Prism picks whichever you configured; see `_resolve_backend()`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE importing the SDKs: google-genai reads its backend and auth
# settings from the environment at import time.
#
# Pinned to THIS project's .env. A bare load_dotenv() walks up parent
# directories, so an unrelated .env higher in your tree can silently point the
# app at a different backend.
#
# override=False on purpose: a variable you exported yourself beats .env, so
# `GOOGLE_CLOUD_PROJECT=my-proj make demo` does what it looks like it does.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from google.adk.models import Gemini  # noqa: E402  (import after dotenv)
from google.genai import types  # noqa: E402


# --- Backend: Gemini API (AI Studio) or Gemini Enterprise Agent Platform ----------------------------
def _resolve_backend() -> tuple[bool, str, str]:
    """Pick the Gemini backend from the environment.

    Returns (use_vertex, project, location). Precedence:
      1. GOOGLE_GENAI_USE_VERTEXAI, if you set it explicitly.
      2. GOOGLE_API_KEY / GEMINI_API_KEY present -> Gemini API (AI Studio).
      3. GOOGLE_CLOUD_PROJECT present            -> Gemini Enterprise Agent Platform.

    Raises with actionable instructions if neither is configured; the
    alternative is a stack trace from deep inside the SDK on the first call.
    The resolved choice is written back to os.environ so every client agrees.
    """
    explicit = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

    if explicit is not None:
        use_vertex = explicit.strip().lower() in ("true", "1", "yes")
    elif api_key:
        use_vertex = False
    elif project:
        use_vertex = True
    else:
        raise RuntimeError(
            "No Gemini backend configured. Set ONE of these in .env "
            "(copy .env.example to .env):\n"
            "  * GOOGLE_API_KEY=...        Gemini API / Google AI Studio\n"
            "                              key: https://aistudio.google.com/apikey\n"
            "  * GOOGLE_CLOUD_PROJECT=...  Gemini Enterprise Agent Platform\n"
            "                              then: gcloud auth application-default login"
        )

    if use_vertex and not project:
        raise RuntimeError(
            "GOOGLE_GENAI_USE_VERTEXAI is true but GOOGLE_CLOUD_PROJECT is not set. "
            "Set your Google Cloud project id in .env, or set GOOGLE_API_KEY "
            "instead to use the Gemini API."
        )
    if not use_vertex and not api_key:
        raise RuntimeError(
            "No GOOGLE_API_KEY / GEMINI_API_KEY found for the Gemini API backend. "
            "Add one to .env (https://aistudio.google.com/apikey), or set "
            "GOOGLE_CLOUD_PROJECT to use Gemini Enterprise Agent Platform instead."
        )

    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true" if use_vertex else "false"
    if use_vertex:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project
        os.environ["GOOGLE_CLOUD_LOCATION"] = location
    return use_vertex, project, location


USE_VERTEXAI, PROJECT_ID, LOCATION = _resolve_backend()
BACKEND_NAME = (
    "Gemini Enterprise Agent Platform" if USE_VERTEXAI else "Gemini API (AI Studio)"
)

# --- Model ------------------------------------------------------------------
# ONE model runs the entire system: gatekeeper, planner, the parallel research
# swarm, and every UI generator. There is deliberately no second/"lite" tier —
# Prism is a single-model demo, so every stage you see on screen is the same
# Gemini 3.7 Flash. It is a plain `gemini-*` id, so ADK attaches the built-in
# google_search tool with no opt-out needed.
MODEL = os.getenv("PRISM_MODEL", "gemini-3.7-flash")

# Public display name. Everything user-visible (frontend, MODES notes,
# /api/modes) reads this, never the raw id — so a model swap is a one-line
# change here and the UI copy never drifts.
MODEL_NAME = os.getenv("PRISM_MODEL_NAME", "Gemini 3.7 Flash")

# --- Latency knobs ----------------------------------------------------------
MAX_WORKERS = int(
    os.getenv("PRISM_MAX_WORKERS", "5")
)  # bounded parallel research swarm
MAX_REPAIRS = int(os.getenv("PRISM_MAX_REPAIRS", "1"))  # self-heal passes
HTML_MAX_CHARS = int(os.getenv("PRISM_HTML_MAX_CHARS", "70000"))
# Output budgets. Raised deliberately: a genuinely animated, self-explaining
# instrument (a real step() loop, a live readout, labelled axes) does not fit in
# the old ceilings, and the budget was being spent on the static scene with the
# motion cut last. These are ceilings, not targets — the prompts set the target.
UI_MAX_OUTPUT_TOKENS = int(
    os.getenv("PRISM_UI_MAX_TOKENS", "32000")
)  # freeform full HTML
FILL_MAX_OUTPUT_TOKENS = int(
    os.getenv("PRISM_FILL_MAX_TOKENS", "16000")
)  # template JS payload

# --- Per-role thinking levels (the core speed/quality dial) ------------------
# One model everywhere, so thinking level — not model choice — is the dial.
#
# NOTE: Gemini 3.7 Flash supports LOW / MEDIUM / HIGH. It does NOT accept
# MINIMAL — passing it fails the request with
# `400 Thinking level is unsupported: THINKING_LEVEL_MINIMAL`.
# LOW is the floor for the latency-sensitive roles.
_TL = types.ThinkingLevel
THINK = {
    "gatekeeper": _TL.LOW,  # fast guardrail/router
    "planner": _TL.LOW,  # quick decomposition
    "worker": _TL.LOW,  # high-volume grounded search
    "ui": _TL.LOW,  # best TTFT + tightest output for streamed HTML
    "fixer": _TL.LOW,  # targeted repair
}


# --- UI generation modes (selectable in the UI; default = balanced) ---------
# 'template' = model writes only the JS payload spliced into shell.html (fast).
# 'full'     = model writes a full bespoke self-contained HTML document (rich).
# Every mode runs the SAME model; the dial is how much it thinks and how much
# of the document it writes. Notes must therefore describe the APPROACH, not a
# model tier — naming a model here would imply a second one exists.
MODES = {
    "fast": {
        "approach": "template",
        "model": MODEL,
        "thinking": _TL.LOW,
        "label": "Fast",
        "note": "Quickest — least deliberation",
    },
    "balanced": {
        "approach": "template",
        "model": MODEL,
        "thinking": _TL.MEDIUM,
        "label": "Balanced",
        "note": "Default — tuned instrument on the studio shell",
    },
    "freeform": {
        "approach": "full",
        "model": MODEL,
        "thinking": _TL.MEDIUM,
        "label": "Freeform",
        "note": "Writes a bespoke UI from scratch",
    },
}
DEFAULT_MODE = os.getenv("PRISM_DEFAULT_MODE", "balanced")


def make_model(model_id: str) -> Gemini:
    """ADK Gemini wrapper with retry on the transient failures this app provokes.

    Two of them are routine here and both are worth surviving rather than
    surfacing to the user mid-run:
      * 429 — the research swarm fires five grounded searches at once.
      * 503 "model is experiencing high demand" — common on the Gemini API
        (AI Studio) tier at busy times; a retry usually succeeds.
    Without the explicit status list only a narrower default set is retried.
    """
    return Gemini(
        model=model_id,
        retry_options=types.HttpRetryOptions(
            attempts=4,
            initial_delay=1.0,
            max_delay=15.0,
            exp_base=2.0,
            jitter=0.3,
            http_status_codes=[429, 500, 502, 503, 504],
        ),
    )


def gen_config(
    role: str,
    *,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> types.GenerateContentConfig:
    """Build a GenerateContentConfig with the role's thinking level."""
    kwargs: dict = {
        "thinking_config": types.ThinkingConfig(thinking_level=THINK[role]),
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = max_output_tokens
    return types.GenerateContentConfig(**kwargs)
