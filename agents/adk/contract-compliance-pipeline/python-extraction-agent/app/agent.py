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

"""ADK orchestration reference for the Contract Compliance Pipeline.

The browser cockpit uses fast_api_app.py for the stable, observable demo path:
deterministic extraction plus a focused ADK RemoteA2aAgent handoff to Go. This
module keeps the fuller ADK agent hierarchy as a reference implementation for
the same cross-language design:

    SequentialAgent (coordinator)
    ├── Agent: extractor_agent      — Parses contracts, extracts key legal fields
    ├── RemoteA2aAgent: compliance_agent  — Sends fields to Go compliance service via A2A
    └── Agent: report_agent         — Generates final audit summary report

Keep this distinction clear in docs and demos: fast_api_app.py runs the live
cockpit path with one focused RemoteA2aAgent call; this file shows the fuller
SequentialAgent architecture.
"""

import os
import google.auth
from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.state_schema import ComplianceStep
from app.tools import (
    read_contract_text,
    save_extracted_fields,
    classify_risk_level,
    generate_summary_report,
)

# Establish Google Cloud project details for Gemini API
try:
    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
except Exception:
    os.environ["GOOGLE_CLOUD_PROJECT"] = "mock-gcp-project"

os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Go compliance agent endpoint (configurable via environment variable)
GO_AGENT_CARD_URL = os.environ.get(
    "GO_AGENT_CARD_URL",
    "http://localhost:8888/.well-known/agent.json"
)


async def initialize_compliance_state(callback_context: CallbackContext) -> None:
    """Initialize pipeline state before the SequentialAgent begins execution.
    
    Sets up all state keys that sub-agents will read and write during the pipeline.
    Using ToolContext.state for shared state is a core ADK pattern — all sub-agents
    in a SequentialAgent share the same session state dictionary.
    """
    state = callback_context.state
    if "current_step" not in state:
        state["current_step"] = ComplianceStep.INGESTED
    if "contract_details" not in state:
        state["contract_details"] = {}
    if "risk_assessment" not in state:
        state["risk_assessment"] = {}
    if "compliance_verdict" not in state:
        state["compliance_verdict"] = {}
    if "trace_logs" not in state:
        state["trace_logs"] = []
    if "final_report" not in state:
        state["final_report"] = {}


# ---------------------------------------------------------------------------
# Sub-Agent 1: Extraction Agent
# ---------------------------------------------------------------------------
# Focused on one job: parse contract text and extract structured legal fields.
# Uses Gemini to understand natural language contract clauses and convert them
# to typed data (floats, dates, booleans).

extractor_agent = Agent(
    name="extractor_agent",
    model=Gemini(
        model="gemini-3.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a Legal Data Extraction Agent.
    Parse contract documents and extract key legal parameters.
    
    Current pipeline state:
    - Step: {current_step}
    - Contract Details: {contract_details}
    
    Instructions:
    1. If current_step is 'INGESTED', use 'read_contract_text' with the contract filename.
    2. Extract these fields from the text:
       - contract_value (float, e.g., 250000.0)
       - contractor_name (the vendor)
       - client_name (the corporate entity)
       - start_date (YYYY-MM-DD)
       - end_date (YYYY-MM-DD)
       - liability_limit (text description, e.g., '$1,000,000' or 'unlimited liability')
       - insurance_coverage (float, minimum coverage amount)
       - auto_renewal (boolean)
       - has_termination_clause (boolean)
    3. Call 'save_extracted_fields' with all extracted parameters.
    4. Call 'classify_risk_level' to determine the risk tier.
    5. Hand control to the next agent.
    """,
    tools=[read_contract_text, save_extracted_fields, classify_risk_level],
)


# ---------------------------------------------------------------------------
# Sub-Agent 2: A2A Compliance Agent (Cross-Language Handoff)
# ---------------------------------------------------------------------------
# This is the key pattern: ADK's RemoteA2aAgent wraps a remote A2A-compliant service
# as a local sub-agent. ADK handles:
#   - Agent Card discovery at the well-known URL
#   - JSON-RPC 2.0 message submission (SendMessage)
#   - Task response conversion back into ADK events
#   - Message/Part serialization
#
# The Go compliance agent runs as a separate process (potentially on a different
# machine, written in a different language) but appears as just another sub-agent
# in the pipeline.

compliance_agent = RemoteA2aAgent(
    name="compliance_agent",
    agent_card=GO_AGENT_CARD_URL,
    description="Validates extracted contract fields against corporate compliance "
                "policy rules via the Go-based Security Compliance Validator service.",
)


# ---------------------------------------------------------------------------
# Sub-Agent 3: Report Agent
# ---------------------------------------------------------------------------
# Generates the final audit summary report from the accumulated state.

report_agent = Agent(
    name="report_agent",
    model=Gemini(
        model="gemini-3.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a Compliance Reporting Specialist.
    Generate the final multi-agent compliance summary report.
    
    Current pipeline state:
    - Step: {current_step}
    - Compliance Verdict: {compliance_verdict}
    - Final Report: {final_report}
    
    Instructions:
    1. Call the 'generate_summary_report' tool.
    2. Present the completed audit summary in clean Markdown:
       - Case ID & Timestamps
       - Contractor Name & Contract Value
       - Risk Tier
       - Compliance Verdict (APPROVED or REJECTED)
       - Specific policy violations (if any)
    3. Hand control back to the coordinator.
    """,
    tools=[generate_summary_report],
)


# ---------------------------------------------------------------------------
# Coordinator: SequentialAgent
# ---------------------------------------------------------------------------
# Runs all three sub-agents in order: extract → comply → report.
# This is the "micro-agent" pattern — each agent has one job, a focused prompt,
# and a narrow tool set. Compare this to a "god agent" that would try to handle
# extraction, compliance checking, and reporting all in a single massive prompt.

root_agent = SequentialAgent(
    name="contract_compliance_coordinator",
    description="Orchestrates contract parsing, A2A compliance validation, "
                "and final reporting in sequence.",
    sub_agents=[extractor_agent, compliance_agent, report_agent],
    before_agent_callback=initialize_compliance_state,
)

app = App(
    root_agent=root_agent,
    name="app",
)
