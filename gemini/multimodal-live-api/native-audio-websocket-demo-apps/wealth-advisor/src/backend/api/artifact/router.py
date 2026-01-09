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


# import uuid
from backend.app_logging import get_logger
from backend.app_settings import get_application_settings
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

# from google.adk.agents import InvocationContext
# from google.adk.events import EventActions
# from google.adk.tools import ToolContext
from google.genai.types import Part

router = APIRouter()
settings = get_application_settings()
logger = get_logger(__name__)


@router.post("/upload/{session_id}")
async def upload_artifact(session_id: str, request: Request, file: UploadFile = File(...)):
    """
    Uploads a file to the artifact service for a specific session.
    """
    logger.info(f"Starting file upload for session_id: {session_id}")

    if not file.filename:
        logger.error("Filename not provided")
        raise HTTPException(status_code=400, detail="Filename not provided")
    logger.info(f"Received file: {file.filename} with content type: {file.content_type}")
    if not file.content_type:
        logger.error("Content-type not provided")
        raise HTTPException(status_code=400, detail="Content-type not provided")

    session_service = request.app.state.session_service
    session = await session_service.get_session(
        app_name=settings.agent.app_name,
        user_id=settings.agent.default_user_id,
        session_id=session_id,
    )
    if not session:
        logger.error(f"Session not found for session_id: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    logger.info(f"Session found for session_id: {session_id}")

    artifact_service = request.app.state.artifact_service
    logger.info("Reading file contents...")
    contents = await file.read()
    logger.info(f"Read {len(contents)} bytes from file.")
    part = Part.from_bytes(data=contents, mime_type=file.content_type)
    logger.info(f"Saving artifact... type {file.content_type}")
    await artifact_service.save_artifact(
        app_name=settings.agent.app_name,
        user_id=settings.agent.default_user_id,
        session_id=session_id,
        filename=file.filename,
        artifact=part,
    )
    available_files = await artifact_service.list_artifact_keys(
        app_name=settings.agent.app_name,
        user_id=settings.agent.default_user_id,
        session_id=session_id,
    )
    # file_list_str = "\n".join([f"- {fname}" for fname in available_files])
    logger.info(f"Listed artifacts: {available_files}")
    logger.info("Artifact saved successfully.")

    return {"filename": file.filename, "status": "uploaded"}
