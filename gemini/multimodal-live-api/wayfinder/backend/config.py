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

"""Configuration loaded from environment variables.

Grounding lives in `VERTEX_SEARCH_ENGINES`, which maps a grounding key (the
widget's `data-tenant`, or the page hostname) to a Agent Search engine:
either the engine resource path as a string, or `{"website_engine": path}`
(the shape `scripts/provision_engine.py` and `scripts/provision_docs.py`
print).
"""

import json
import os
import subprocess

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

# ADK / google-genai default to the Gemini Developer API (API key). Wayfinder
# runs on Agent Platform with Application Default Credentials, so make that the
# default unless explicitly overridden.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("true", "1", "yes", "on")


# ---- Google Cloud ----


def get_project_id() -> str:
    """Google Cloud project from the environment, falling back to gcloud config."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if project:
        return project
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        project = result.stdout.strip()
        if project and project != "(unset)":
            os.environ.setdefault(
                "GOOGLE_CLOUD_PROJECT", project
            )  # for ADK's Vertex client
            return project
    except (OSError, subprocess.SubprocessError):
        pass  # gcloud missing or slow; fall through to the error below
    raise RuntimeError(
        "No Google Cloud project found. Set GOOGLE_CLOUD_PROJECT in .env or run: "
        "gcloud config set project YOUR_PROJECT_ID"
    )


def get_location() -> str:
    """Agent Platform location for model calls.

    Defaults to the `us` multi-region, which serves both Gemini 3.8 Live
    (voice) and Gemini 3.8 Flash (text). Gemini 3.8 Flash isn't available in
    us-central1.
    """
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us")
    # ADK's Vertex client reads these from the environment.
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", location)
    return location


# ---- Models ----


def get_model() -> str:
    """Voice model (Gemini Live API).

    Defaults to the GA Gemini 3.8 Live model. To try Gemini 3.8 Live Extended
    Thinking, set GEMINI_MODEL to its model ID in a project with access; the
    voice agent then switches to async (NON_BLOCKING) tools and a thinking
    level automatically, and falls back to `get_fallback_model()` if the
    session can't start.
    """
    return os.environ.get("GEMINI_MODEL", "gemini-3.8-live")


def get_fallback_model() -> str:
    """Voice model used when the configured model can't start a session."""
    return os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.8-live")


def get_text_model() -> str:
    """Model for the text transport (ADK runner)."""
    return os.environ.get("GEMINI_TEXT_MODEL", "gemini-3.8-flash")


# ---- Live API (voice) ----


def get_live_thinking_level() -> str:
    """Background reasoning level for Gemini 3.8 Live Extended Thinking:
    LOW, MEDIUM, or HIGH (MINIMAL isn't supported by that model).
    """
    level = os.environ.get("LIVE_THINKING_LEVEL", "MEDIUM").strip().upper()
    return level if level in ("LOW", "MEDIUM", "HIGH") else "MEDIUM"


def get_live_voice() -> str:
    """Prebuilt voice for Live API audio output."""
    return os.environ.get("LIVE_VOICE", "Aoede")


def get_live_proactive_audio() -> bool:
    """Let the Live model ignore background speech not addressed to it."""
    return _env_flag("LIVE_PROACTIVE_AUDIO", True)


def get_live_affective_dialog() -> bool:
    """Let the Live model adapt tone to the user's emotional cues."""
    return _env_flag("LIVE_AFFECTIVE_DIALOG", False)


def get_live_context_compression() -> bool:
    """Sliding-window context compression for long sessions."""
    return _env_flag("LIVE_CONTEXT_COMPRESSION", True)


def get_live_async_search() -> bool:
    """Run knowledge search as a NON_BLOCKING tool so the agent keeps talking
    while it searches. Ignored by models without support.
    """
    return _env_flag("LIVE_ASYNC_SEARCH", True)


# ---- Grounding (Agent Search) ----


def get_vertex_search_engines() -> dict[str, object]:
    """Raw mapping of grounding key -> engine config (string or dict)."""
    raw = os.environ.get("VERTEX_SEARCH_ENGINES", "{}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def get_tenant_config(key: str) -> dict:
    """Normalized per-tenant RAG config: {"website_engine": path or None}."""
    raw = get_vertex_search_engines().get(key)
    if isinstance(raw, str):
        return {"website_engine": raw}
    if isinstance(raw, dict):
        return {"website_engine": raw.get("website_engine")}
    return {"website_engine": None}


# ---- Server / auth ----


def get_allowed_origins() -> list[str]:
    """CORS allowlist of full origins, e.g. "https://acme.com"; "*" for any."""
    raw = os.environ.get("ALLOWED_ORIGINS", "*")
    if raw.strip() == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def get_reload() -> bool:
    """Uvicorn auto-reload. Dev only; the container entrypoint never sets it."""
    return _env_flag("RELOAD", False)


def get_api_keys() -> dict[str, dict]:
    """API key configuration.

    Format: {"wf_abc123": {"name": "Acme Corp", "origins": ["acme.com"]}}
    Set via API_KEYS (JSON) or API_KEYS_FILE (path to a JSON file).
    """
    keys_file = os.environ.get("API_KEYS_FILE")
    if keys_file and os.path.exists(keys_file):
        with open(keys_file) as f:
            return json.load(f)
    raw = os.environ.get("API_KEYS", "")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def get_self_origin() -> str:
    """The service's own hostname (e.g. "wayfinder-abc123-uc.a.run.app").
    Requests from this origin skip API-key checks (co-hosted pages).
    """
    return os.environ.get("SELF_ORIGIN", "").strip()


def get_auth_enabled() -> bool:
    """API-key + origin checks. Off by default for local development."""
    return _env_flag("AUTH_ENABLED", False)
