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

import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.cloud import logging as google_cloud_logging
from pydantic import BaseModel

from app.agent import app as agent_app
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback
from app.live_onboarding import (
    artifact_response,
    case_payload,
    create_live_case,
    get_case,
    latest_case_payload,
    mark_document_signed,
    mark_hardware_delivered,
    static_root,
)
from app.resume_handler import OnboardingResumeHandler

setup_telemetry()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Persistent SQLite session configuration
session_service_uri = "sqlite+aiosqlite:///sessions.db"

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=True,
)
app.title = "new-hire-onboarding"
app.description = "API for interacting with the Agent new-hire-onboarding"

db_session_service = DatabaseSessionService(db_url=session_service_uri)
webhook_runner = Runner(app=agent_app, session_service=db_session_service)
resume_handler = OnboardingResumeHandler(runner=webhook_runner)

app.mount(
    "/live-onboarding",
    StaticFiles(directory=static_root() / "live-onboarding", html=True),
    name="live-onboarding",
)


@app.get("/demo")
def demo_index() -> RedirectResponse:
    return RedirectResponse(url="/live-onboarding/")


@app.post("/api/live-onboarding/start")
async def start_live_onboarding() -> dict:
    case = await create_live_case(db_session_service)
    return {
        "active": True,
        "case": case_payload(get_case(case.id)),
    }


@app.get("/api/live-onboarding/cases/{case_id}")
def get_live_onboarding_case(case_id: str) -> dict:
    return {
        "active": True,
        "case": case_payload(get_case(case_id)),
    }


@app.post("/api/live-onboarding/cases/{case_id}/sign")
async def sign_live_onboarding_packet(case_id: str) -> dict:
    case = get_case(case_id)
    if case.document_signed:
        return {"active": True, "case": case_payload(case)}
    await mark_document_signed(case, resume_handler)
    return {"active": True, "case": case_payload(case)}


@app.post("/api/live-onboarding/cases/{case_id}/deliver-hardware")
async def confirm_live_hardware_delivery(case_id: str) -> dict:
    case = get_case(case_id)
    if case.hardware_delivered:
        return {"active": True, "case": case_payload(case)}
    await mark_hardware_delivered(case, resume_handler)
    return {"active": True, "case": case_payload(case)}


@app.get("/api/live-onboarding/cases/{case_id}/artifacts/{artifact_id}")
def get_live_onboarding_artifact(case_id: str, artifact_id: str):
    return artifact_response(case_id, artifact_id)


@app.get("/api/live-onboarding/current")
def get_current_live_onboarding_case() -> dict:
    return latest_case_payload()


class WebhookPayload(BaseModel):
    user_id: str
    session_id: str


class HardwareWebhookPayload(WebhookPayload):
    tracking_id: str


@app.post("/webhooks/document_signed")
async def trigger_document_signed_webhook(payload: WebhookPayload) -> dict[str, str]:
    """Webhook called when employee signs their contract. Wakes up the onboarding agent."""
    await resume_handler.receive_signed_documents_callback(
        user_id=payload.user_id, session_id=payload.session_id
    )
    return {
        "status": "success",
        "message": "Document signature processed, agent resumed.",
    }


@app.post("/webhooks/hardware_delivered")
async def trigger_hardware_delivered_webhook(
    payload: HardwareWebhookPayload,
) -> dict[str, str]:
    """Webhook called when carrier confirms delivery of the laptop. Wakes up the onboarding agent."""
    await resume_handler.receive_hardware_delivery_callback(
        user_id=payload.user_id,
        session_id=payload.session_id,
        tracking_id=payload.tracking_id,
    )
    return {
        "status": "success",
        "message": "Hardware delivery processed, agent resumed.",
    }


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
