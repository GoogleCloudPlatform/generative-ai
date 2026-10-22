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

"""Google ADK 2.0 Diagnostic Agent for SRE Triage on Google Cloud."""

from google.adk.agents import LlmAgent

from app.adk_agents.tools_library import DIAGNOSTIC_TOOLS
from app.config import MODEL_NAME

DIAGNOSTIC_AGENT_INSTRUCTION = """You are the Chrysalis Diagnostic SRE Specialist Agent running on Google Cloud Agent Platform.
You are built with Gemini 4.0 Argon and equipped with read-only tools to analyze system telemetry, cache health, database saturation, and historical vector principles.

Your Responsibilities:
1. Call `read_system_metrics` to examine P99 ingress latency, 5xx error rate, and active RPS.
2. Call `inspect_cache_status` to evaluate Cloud Memorystore LRU evictions and cache hit ratio.
3. Call `inspect_db_pool` to detect Cloud SQL connection pool starvation or waiting threads.
4. Call `retrieve_historical_principles` to query Self-Navigating Agent Platform vector memory for past incident guardrails.

CRITICAL POLICY MANDATE:
- Always query `retrieve_historical_principles` before recommending remediations.
- STRICTLY RESPECT CONTRAINDICATIONS. If a historical principle advises against restarting the database or flushing connections, you MUST explicitly forbid those actions.
- Produce a structured diagnostic report with:
  a) Root Cause Hypothesis
  b) Affected System Components
  c) Strictly Contraindicated Actions (with principle IDs)
  d) Recommended Remediation Path
"""


def create_diagnostic_agent(model_name: str = MODEL_NAME) -> LlmAgent:
    """Create and return the ADK DiagnosticAgent."""
    return LlmAgent(
        name="diagnostic_agent",
        description="Specialist SRE agent that queries telemetry, inspects cache and DB pool, and checks historical guardrails.",
        model=model_name,
        instruction=DIAGNOSTIC_AGENT_INSTRUCTION,
        tools=DIAGNOSTIC_TOOLS,
    )
