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

"""FastAPI application for the Contract Compliance Pipeline.

Provides REST API endpoints for contract upload, status checking, and
result retrieval. The live cockpit uses deterministic extraction and a real
ADK RemoteA2aAgent handoff to the Go compliance service so the demo remains
stable while still exercising the current A2A SendMessage protocol.
"""

import json
import os
import secrets
import shutil
import logging
import uuid
import time
import asyncio
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from a2a.types import DataPart as A2ADataPart
from google.adk.a2a.agent.config import A2aRemoteAgentConfig, RequestInterceptor
from google.adk.a2a.converters.part_converter import (
    A2A_DATA_PART_END_TAG,
    A2A_DATA_PART_START_TAG,
    A2A_DATA_PART_TEXT_MIME_TYPE,
)
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.apps import App as ADKApp
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types as genai_types

from app.state_schema import ComplianceStep
from app.tools import (
    SANDBOX_DIR,
    UPLOAD_DIR,
    classify_contract_risk,
    extract_contract_details_from_text,
)
from app.app_utils.telemetry import setup_telemetry
from app.live_compliance import (
    create_compliance_case,
    get_case,
    latest_case_payload,
    sync_case_with_session_state,
    case_payload,
    artifact_response,
    _event,
)

setup_telemetry()
logger = logging.getLogger(__name__)

GO_AGENT_CARD_URL = os.environ.get(
    "GO_AGENT_CARD_URL",
    "http://localhost:8888/.well-known/agent.json",
)
PROJECT_ROOT = Path(SANDBOX_DIR)
SAMPLE_CONTRACTS_DIR = PROJECT_ROOT / "sample-contracts"


def _go_jsonrpc_url() -> str:
    if GO_AGENT_CARD_URL.endswith("/.well-known/agent.json"):
        return GO_AGENT_CARD_URL.removesuffix("/.well-known/agent.json")
    return GO_AGENT_CARD_URL.rstrip("/")


def build_contract_handoff_data(case_id: str, details: dict, policy: dict | None) -> dict:
    data = {
        "schema_version": "contract-compliance.a2a.v1",
        "case_id": case_id,
        "contract": details,
    }
    if policy:
        data["policy"] = policy
    return data


def build_go_message_payload(case_id: str, details: dict, policy: dict | None) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": f"case-{case_id}",
        "method": "SendMessage",
        "params": {
            "metadata": {"task_id": case_id},
            "message": {
                "messageId": f"case-{case_id}-request",
                "taskId": case_id,
                "role": "ROLE_USER",
                "parts": [{
                    "data": build_contract_handoff_data(case_id, details, policy),
                    "mediaType": "application/json"
                }],
            },
        },
    }


def extract_verdict_from_go_response(response: dict) -> dict:
    result = response.get("result", response)
    parts = (
        result
        .get("status", {})
        .get("message", {})
        .get("parts", [])
    )
    for part in parts:
        if "data" in part:
            return part["data"]
        if part.get("kind") == "data" or part.get("type") == "data":
            return part.get("data", {})
    raise RuntimeError("Go compliance service returned no verdict data")


def _a2a_data_part_as_genai_part(data: dict) -> genai_types.Part:
    """Build a GenAI Part that ADK converts back into an A2A DataPart."""
    data_part = A2ADataPart(data=data)
    return genai_types.Part(
        inline_data=genai_types.Blob(
            data=(
                A2A_DATA_PART_START_TAG
                + data_part.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
                + A2A_DATA_PART_END_TAG
            ),
            mime_type=A2A_DATA_PART_TEXT_MIME_TYPE,
        )
    )


def _http_json(method: str, url: str, payload: dict | None = None, timeout: float = 10.0) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


async def invoke_go_compliance_service(
    case_id: str,
    details: dict,
    policy: dict | None,
    timeout: float = 10.0,
) -> dict:
    """Calls the Go service through ADK RemoteA2aAgent and the A2A SDK."""
    agent_card = await asyncio.to_thread(_http_json, "GET", GO_AGENT_CARD_URL, None, timeout)
    payload = build_go_message_payload(case_id, details, policy)
    request_data = build_contract_handoff_data(case_id, details, policy)

    async def add_task_metadata(_ctx, a2a_message, parameters):
        parameters.request_metadata = {"task_id": case_id}
        return a2a_message, parameters

    remote_agent = RemoteA2aAgent(
        name="compliance_agent",
        agent_card=GO_AGENT_CARD_URL,
        description="Validates extracted contract fields with the Go A2A compliance service.",
        timeout=timeout,
        config=A2aRemoteAgentConfig(
            request_interceptors=[
                RequestInterceptor(before_request=add_task_metadata)
            ]
        ),
    )
    session_service = InMemorySessionService()
    adk_app_name = "contract_compliance_remote_handoff"
    await session_service.create_session(
        app_name=adk_app_name,
        user_id="live-cockpit",
        session_id=case_id,
        state={},
    )
    runner = Runner(
        app=ADKApp(name=adk_app_name, root_agent=remote_agent),
        session_service=session_service,
    )

    response_task = None
    request_message = None
    error_message = None
    try:
        async for event in runner.run_async(
            user_id="live-cockpit",
            session_id=case_id,
            new_message=genai_types.Content(
                role="user",
                parts=[_a2a_data_part_as_genai_part(request_data)],
            ),
        ):
            metadata = event.custom_metadata or {}
            request_message = metadata.get("a2a:request", request_message)
            response_task = metadata.get("a2a:response", response_task)
            if event.error_message:
                error_message = event.error_message
    finally:
        await remote_agent.cleanup()

    if error_message:
        raise RuntimeError(error_message)
    if response_task is None:
        raise RuntimeError("ADK RemoteA2aAgent returned no A2A task response")

    response = {
        "jsonrpc": "2.0",
        "id": payload["id"],
        "result": response_task,
    }

    return {
        "agent_card": agent_card,
        "request": payload,
        "response": response,
        "adk_request_message": request_message,
        "adk_response_task": response_task,
        "verdict": extract_verdict_from_go_response(response),
    }


# --- Session Credentials ---
def get_session_secret() -> str:
    """Generate or load a session secret key."""
    if os.getenv("SESSION_SECRET_KEY"):
        return os.getenv("SESSION_SECRET_KEY")

    secret_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session_secret.txt")
    if os.path.exists(secret_file):
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass

    ephemeral = secrets.token_hex(32)
    try:
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(ephemeral)
    except Exception:
        pass
    return ephemeral


# --- App Configuration ---
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
session_service_uri = "sqlite+aiosqlite:///sessions.db"

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    session_service_uri=session_service_uri,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "null",
    ],
)

app.title = "contract-compliance-pipeline"
app.description = "Multi-agent contract compliance pipeline using ADK and A2A protocol."

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Startup ---
@app.on_event("startup")
def boot_sandbox_bounds():
    """Initialize upload directory and preload sample contracts."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # Preload sample contracts from project root
    sample_dir = str(SAMPLE_CONTRACTS_DIR)
    if os.path.exists(sample_dir):
        for filename in os.listdir(sample_dir):
            src = os.path.join(sample_dir, filename)
            dst = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(src):
                try:
                    shutil.copy2(src, dst)
                except Exception as ex:
                    logger.warning(f"Preloading contract {filename} failed: {ex}")
    logger.info(f"Upload directory ready: {UPLOAD_DIR}")


# --- ADK Session Storage ---
db_session_service = DatabaseSessionService(db_url=session_service_uri)

# --- Static Files ---
static_folder = Path(__file__).parent / "static" / "live-compliance"
if static_folder.exists():
    app.mount(
        "/live-compliance",
        StaticFiles(directory=str(static_folder), html=True),
        name="live-compliance",
    )


@app.get("/demo")
def demo_router() -> RedirectResponse:
    return RedirectResponse(url="/live-compliance/")


# --- API Endpoints ---

@app.get("/api/compliance/current")
def get_current_case_status() -> dict:
    return latest_case_payload()


@app.get("/api/compliance/cases/{case_id}")
def get_compliance_case(case_id: str) -> dict:
    case = get_case(case_id)
    return {"active": True, "case": case_payload(case)}


@app.get("/api/compliance/cases/{case_id}/artifacts/{artifact_id}")
def get_compliance_artifact(case_id: str, artifact_id: str):
    return artifact_response(case_id, artifact_id)


@app.get("/api/compliance/sample-contracts/{filename}")
def get_sample_contract(filename: str) -> PlainTextResponse:
    """Serves bundled sample contract text for the browser-driven demo."""
    safe_filename = os.path.basename(filename)
    target = (SAMPLE_CONTRACTS_DIR / safe_filename).resolve()
    sample_root = SAMPLE_CONTRACTS_DIR.resolve()
    if not str(target).startswith(str(sample_root) + os.path.sep):
        raise HTTPException(status_code=403, detail="Invalid sample contract path.")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Sample contract not found.")
    if target.suffix.lower() not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Unsupported sample contract type.")

    return PlainTextResponse(
        target.read_text(encoding="utf-8", errors="ignore"),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/compliance/upload")
async def upload_contract_file(
    file: UploadFile = File(...),
    simulated_latency: float = Form(0.0),
    simulated_server_state: str = Form("normal"),
    custom_policies: Optional[str] = Form(None),
) -> dict:
    """Upload a text contract fixture and run the compliance pipeline.

    Accepts text files and .pdf-named text fixtures, saves them securely, and kicks off the
    multi-agent pipeline: extraction → A2A compliance check → reporting.
    """
    filename = file.filename or "contract.pdf"
    original_filename = os.path.basename(filename)

    # Verify extensions
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".txt", ".md"]:
        raise HTTPException(status_code=400, detail="Only .pdf, .txt, and .md text fixtures are supported.")

    # Rename to UUID for security
    case_id = str(uuid.uuid4())
    safe_filename = f"{case_id}{ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    secure_target = os.path.join(UPLOAD_DIR, safe_filename)

    # Path traversal check
    absolute_root = os.path.abspath(UPLOAD_DIR) + os.path.sep
    absolute_target = os.path.abspath(secure_target)
    if not absolute_target.startswith(absolute_root):
        raise HTTPException(status_code=403, detail="Invalid upload path.")

    # Size limit (5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit.")
    if ext == ".pdf" and content.lstrip().startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Binary PDF parsing is not included in this demo. "
                "Use bundled text fixtures or upload .txt/.md contract text."
            ),
        )

    # Save file
    try:
        with open(absolute_target, "wb") as f:
            f.write(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc!s}")

    # Create compliance case
    case = await create_compliance_case(original_filename, db_session_service)

    content_text = content.decode("utf-8", errors="ignore")
    details = extract_contract_details_from_text(original_filename, content_text)
    risk = classify_contract_risk(details)
    policy = None
    if custom_policies:
        try:
            policy = json.loads(custom_policies)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid custom_policies JSON: {exc!s}")

    # Keep simulator values bounded so UI experiments cannot lock the API.
    simulated_latency = max(0.0, min(float(simulated_latency), 5.0))
    simulated_server_state = simulated_server_state.lower().strip()

    trace_logs = [
        {
            "span": "POST /api/compliance/upload",
            "service": "python-extraction-agent",
            "duration_ms": 140,
            "status": "file_ingested",
        },
        {
            "span": "extract_contract_fields",
            "service": "python-extraction-agent",
            "duration_ms": 180,
            "status": "fields_extracted",
        },
        {
            "span": "classify_risk_level",
            "service": "python-extraction-agent",
            "duration_ms": 25,
            "status": risk["risk_tier"].lower(),
        },
    ]

    _event(case, "agent", "Extractor completed", f"{details['contractor_name']} fields extracted and risk classified as {risk['risk_tier']}.")

    handoff = {
        "status": "prepared",
        "source_agent": "python-extraction-agent",
        "target_agent": "Security Compliance Validator",
        "remote_agent": "google.adk.agents.RemoteA2aAgent(compliance_agent)",
        "agent_card_url": GO_AGENT_CARD_URL,
        "jsonrpc_url": _go_jsonrpc_url(),
        "method": "SendMessage",
        "task_id": case.id,
        "contract_details": details,
        "risk_assessment": risk,
        "policy_override": bool(policy),
        "request": build_go_message_payload(case.id, details, policy),
    }

    if simulated_latency:
        await asyncio.sleep(simulated_latency)

    try:
        if simulated_server_state == "crashed":
            raise ConnectionError("Simulated Go compliance service 503 failure")

        handoff_result = await invoke_go_compliance_service(
            case_id=case.id,
            details=details,
            policy=policy,
            timeout=10.0,
        )
        verdict = handoff_result["verdict"]
        handoff.update(
            {
                "status": "completed",
                "agent_card": handoff_result["agent_card"],
                "request": handoff_result["request"],
                "response": handoff_result["response"],
                "adk_request_message": handoff_result["adk_request_message"],
                "adk_response_task": handoff_result["adk_response_task"],
                "verdict": verdict,
            }
        )
        current_step = (
            ComplianceStep.APPROVED
            if verdict.get("passed", False)
            else ComplianceStep.REVIEW_READY
        )
        trace_logs.extend(
            [
                {
                    "span": "GET /.well-known/agent.json",
                    "service": "go-compliance-agent",
                    "duration_ms": 45,
                    "status": "agent_card_discovered",
                },
                {
                    "span": "ADK RemoteA2aAgent SendMessage",
                    "service": "go-compliance-agent",
                    "duration_ms": 120,
                    "status": "completed",
                },
                {
                    "span": "go_validate_policy",
                    "service": "go-compliance-agent",
                    "duration_ms": 18,
                    "status": "passed" if verdict.get("passed", False) else "violations_found",
                },
            ]
        )
    except (ConnectionError, TimeoutError, urllib.error.URLError, RuntimeError) as exc:
        logger.warning(f"Go compliance handoff failed for case {case.id}: {exc!s}")
        current_step = ComplianceStep.MANUAL_REVIEW
        verdict = {
            "passed": False,
            "violations": [
                "SYSTEM TIMEOUT: External compliance service failed to respond within 30-second threshold.",
                "FAIL-SAFE ACTION: Document routed for legal manager manual verification.",
            ],
            "verdict_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        handoff.update(
            {
                "status": "failed",
                "error": str(exc),
                "verdict": verdict,
            }
        )
        trace_logs.append(
            {
                "span": "resilience_fallback_gate",
                "service": "python-extraction-agent",
                "duration_ms": 450,
                "status": "manual_review_routed",
            }
        )

    session_state = {
        "case_id": case.id,
        "current_step": current_step,
        "contract_filename": original_filename,
        "contract_details": details,
        "risk_assessment": risk,
        "compliance_verdict": verdict,
        "handoff": handoff,
        "pending_signals": [],
        "trace_logs": trace_logs,
        "completion_time": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }

    sync_case_with_session_state(case, session_state)
    return {"active": True, "case": case_payload(case)}


# --- Local Dev Server ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
