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

"""Configuration for Project Chrysalis: Agent Platform Version on Google Cloud."""

import logging
import os
import warnings

# google-auth shells out to `gcloud config get project` (a fork) whenever user ADC credentials are
# resolved. gRPC's fork handlers then run in that short-lived child (which immediately execs gcloud),
# producing noisy "FD from fork parent" / resolver check-failure logs. The child never uses gRPC,
# so disable gRPC fork support and keep C-core logging at ERROR (must be set before grpc is imported).
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "false")
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")


def _resolve_gcp() -> tuple:
    """Resolve (project_id, credentials_available).

    Project: $GOOGLE_CLOUD_PROJECT, else Application Default Credentials / gcloud config.
    Credentials: whether ADC can be loaded at all. Without them every Gemini call would fail, so
    agents skip straight to their deterministic offline fallbacks (set CHRYSALIS_OFFLINE=1 to force).
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_available = False
    if os.getenv("CHRYSALIS_OFFLINE", "").lower() not in ("1", "true", "yes"):
        try:
            import google.auth  # pylint: disable=import-outside-toplevel

            _, adc_project = google.auth.default()
            credentials_available = True
            project = project or adc_project
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    return project or "your-gcp-project-id", credentials_available


PROJECT_ID, VERTEX_AI_AVAILABLE = _resolve_gcp()
# Number of live LLM attempts per agent invocation (0 => deterministic offline fallback only)
LLM_MAX_ATTEMPTS: int = 3 if VERTEX_AI_AVAILABLE else 0
LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
REGION: str = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

# GOOGLE_GENAI_USE_ENTERPRISE supersedes the deprecated GOOGLE_GENAI_USE_VERTEXAI in
# google-adk >= 2.9 / google-genai >= 2.x; both are set (consistently) for compatibility.
os.environ.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "True")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = os.environ["GOOGLE_GENAI_USE_ENTERPRISE"]
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = LOCATION


class _DropAdkCacheHint(logging.Filter):
    """Suppress ADK's advisory 'no context_cache_config' hint (performance tip, not an error)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "context_cache_config" not in record.getMessage()


logging.getLogger("google_adk.google.adk.runners").addFilter(_DropAdkCacheHint())
warnings.filterwarnings(
    "ignore", message=r"\[EXPERIMENTAL\] feature FeatureName\.JSON_SCHEMA_FOR_FUNC_DECL"
)

# Agent Platform Model settings
MODEL_NAME: str = os.getenv("GEMINI_MODEL", "gemini-4-argon")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

# Google Cloud Services configuration
BIGQUERY_DATASET: str = os.getenv("CHRYSALIS_BQ_DATASET", "chimera_telemetry")
BIGQUERY_REQUESTS_TABLE: str = "recorded_requests"
BIGQUERY_SIMULATIONS_TABLE: str = "counterfactual_runs"

CLOUD_LOG_NAME: str = "chimera-security-audit"
CLOUD_METRIC_PREFIX: str = "custom.googleapis.com/chrysalis"

# Cloud KMS Governance Settings
KMS_LOCATION: str = "us-central1"
KMS_KEY_RING: str = "chimera-governance-ring"
KMS_KEY_NAME: str = "chimera-patch-signer"

# Governance & Safety thresholds
POLICY_MIN_ADMIT_RATE: float = 10.0  # SLA minimum throughput floor (req/s)
POLICY_MAX_CAPACITY: int = 100  # Maximum token buffer size
POLICY_CANARY_TRAFFIC_PCT: float = 0.05  # 5% canary split
MAX_AGENT_HOPS_PER_INCIDENT: int = 4
MAX_LLM_TOKEN_BUDGET: int = 50_000

# Server configuration
SERVER_HOST: str = "127.0.0.1"
SERVER_PORT: int = 8009  # Port 8009 for Agent Platform version
