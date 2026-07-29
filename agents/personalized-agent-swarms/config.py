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

"""Central configuration for the Active Long Memory pipeline.

Single source of truth for the Google Cloud project, Google Cloud location, and the model
IDs used across every phase (harvest, analyze, augment, evaluate). Import this
module instead of hardcoding project/model literals.

Location note: all models used here (Gemini 3.x, Gemini 2.5, text-embedding-005)
are served on the Google Cloud ``global`` endpoint, so a single ``LOCATION`` value
is correct for every client. If you ever target a model/region where ``global``
is not served, set ``GOOGLE_CLOUD_LOCATION`` in ``.env`` accordingly.
"""

from __future__ import annotations

import os
import pathlib

from dotenv import load_dotenv

# Load the project-root .env so PROJECT/LOCATION are populated regardless of
# which script imports this module first.
load_dotenv(pathlib.Path(__file__).parent / ".env")

# --- Google Cloud / Google Cloud ---------------------------------------------------------
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

# --- Models by role ----------------------------------------------------------
# Agent runtime + mini-agents (baseline & augmented assistants, harvest assistant).
AGENT_MODEL = "gemini-3-flash-preview"

# Simulated user in the harvest phase.
USER_SIM_MODEL = "gemini-2.5-flash"

# Assistant used during the harvest phase (cheaper than the runtime agent for
# bulk history generation).
HARVEST_ASSISTANT_MODEL = "gemini-2.5-flash"

# Simulated user during evaluation (stronger model than harvest for higher-
# quality test turns).
EVAL_USER_SIM_MODEL = "gemini-3-flash-preview"

# Trigger matching: feature extraction + questionnaire eval.
TRIGGER_MODEL = "gemini-2.5-flash"

# Web-search sub-agent (currently unused; kept for parity).
SEARCH_AGENT_MODEL = "gemini-2.5-flash"

# Analysis / pattern extraction / swarm generation (with fallbacks).
ANALYSIS_MODEL = "gemini-3.1-pro-preview"
ANALYSIS_FALLBACKS = ["gemini-3-pro-preview", "gemini-2.5-pro"]

# LLM-as-judge for evaluation (with fallbacks).
JUDGE_MODEL = "gemini-3.1-pro-preview"
JUDGE_FALLBACKS = ["gemini-2.5-pro"]

# Higher-quality review/confirmation passes (eval sampler, trigger match check).
REVIEW_MODEL = "gemini-2.5-pro"

# Text embeddings (semantic similarity everywhere).
EMBED_MODEL = "text-embedding-005"


def new_client():
    """Return a Google Cloud genai client bound to the configured project/location.

    A single shared-config client (not a per-model factory) — every model above
    is served at ``LOCATION``, so callers can reuse one client for all calls.
    """
    from google import genai

    return genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
