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


import json
import traceback
from pathlib import Path

from typing import (
    Any,
    AsyncGenerator,
)
from urllib.parse import unquote

from backend.app_logging import get_logger

from backend.app_settings import ApplicationSettings, get_application_settings
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.adk.agents import LiveRequestQueue

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import Session
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from google.cloud import firestore
from google.genai import types
from starlette.websockets import WebSocketState

from .services import get_connect_and_run_callable

websocket_router = APIRouter(prefix="/websocket", tags=["Websocket"])
app_settings = get_application_settings()
logger = get_logger(__name__)


def get_user_profile(user_id: str) -> dict:
    """
    Retrieves the user profile, preferring Firestore but falling back to local JSON.
    """
    client_data = {}

    # 1. Try Firestore
    try:
        # Use ADC; no explicit key path needed if environment is set up correctly
        db = firestore.Client(
            project=app_settings.google_cloud.project_id, database=app_settings.google_cloud.firestore_db_name
        )
        # We might want to use a generic ID or the passed user_id if we have real auth
        firestore_user_id = "financial_advisor_demo_user"
        user_ref = db.collection("users").document(firestore_user_id)
        doc_ref = user_ref.collection("client_data").document("profile")
        doc = doc_ref.get()
        if doc.exists:
            logger.info("Loaded client profile from Firestore.")
            return doc.to_dict()
    except Exception as e:
        logger.info(f"Firestore profile not found (using local demo data). Error: {e}")

    # 2. Fallback to Local JSON
    try:
        json_path = Path(__file__).parent.parent.parent / "data" / "client_data.json"
        with open(json_path, "r") as f:
            client_data = json.load(f)
            logger.info("Loaded client profile from local JSON.")
            return client_data
    except Exception as e:
        logger.error(f"Failed to load local client_data.json: {e}")
        return {}


async def _initialize_agent_system_components(
    websocket: WebSocket,
    session_id: str,
    app_settings: ApplicationSettings,
    initial_state: dict,
    session_service: InMemorySessionService,
    artifact_service: InMemoryArtifactService,
    is_audio: bool = False,
    notification_text: str = "",
) -> tuple[Session, Runner, RunConfig, LiveRequestQueue, AsyncGenerator[Any, None]]:
    """Initializes and starts an agent session, returning its key components."""

    notification_instructions = ""
    if notification_text != "":
        notification_instructions = f"""
        NOTIFICATION INSTRUCTIONS - IMMEDIATE ACTION REQUIRED: {initial_state["user_name"]} has just clicked on a notification with the following content: '{notification_text}'.
        Your immediate and only first action should be to greet them and ask if they would like to discuss the <TOPIC> of the notification. For example,
        Hi {initial_state["user_name"]}, thanks for logging in. I hope you are doing well today. I see you have clicked on the notification about <TOPIC>. 
        Would you like to discuss this in greater detail?
        """
    initial_state["notification_instructions"] = notification_instructions

    root_agent = websocket.app.state.root_agent

    runner = Runner(
        app_name=app_settings.agent.app_name,
        agent=root_agent,
        session_service=session_service,
        artifact_service=artifact_service,
    )

    session = None
    try:
        session = await session_service.get_session(
            app_name=app_settings.agent.app_name,
            user_id="generic_user",
            session_id=session_id,
        )
    except Exception as e:
        logger.info(f"Could not get existing session for {session_id}: {e}. A new session will be created.")

    if session is None:
        session = await session_service.create_session(
            app_name=app_settings.agent.app_name,
            user_id="generic_user",
            state=initial_state,
            session_id=session_id,
        )

    modality = "AUDIO"

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=app_settings.voice.voice_name)
            )
        ),
        response_modalities=[modality],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        input_audio_transcription=types.AudioTranscriptionConfig(),
    )

    live_request_queue = LiveRequestQueue()
    live_events = runner.run_live(
        user_id="generic_user",
        session_id=session_id,
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return session, runner, run_config, live_request_queue, live_events


@websocket_router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    is_audio: str = "false",
    notification_text: str = "",
):
    """
    Handles a new client connection.
    """
    logger.info("New connection...")
    await websocket.accept()

    try:
        # Load Client Data (Abstracted)
        client_data = get_user_profile(session_id)

        # Determine User Name safely
        user_name = "User"
        if "clientDetails" in client_data and "name" in client_data["clientDetails"]:
            user_name = client_data["clientDetails"]["name"].get("firstName", "User")

        # Mock CD Information (Genericized)
        cd_info_text = ""
        if notification_text != "":
            cd_info_text = (
                f"{user_name} has a certificate of deposit (CD) that is a part of their emergency fund. "
                f"Remember this fact whenever {user_name} and you discuss CD options. Do NOT forget to include it when discussing CD information. "
                "The CD is maturing on October 31, 2025. It will have a balance of $10,074.17. "
                "The CD was paying 3% APY over 3 months. One option for managing the maturing CD, is to reinvest into a new CD. "
                f"{app_settings.bank_name} currently offers a 3 month CD with a 3.25% APY, a 4 month CD with a 3.5% APY and a 6 month CD with a 4% APY."
                f"Leverage this information as context to respond to {user_name} as needed."
            )

        initial_state = {
            "profile": client_data,
            "user_name": user_name,
            "cd_information": cd_info_text,
            "advisor_name": app_settings.advisor_name,
            "bank_name": app_settings.bank_name,
        }

        session_service = websocket.app.state.session_service
        artifact_service = websocket.app.state.artifact_service

        _, _, _, live_request_queue, live_events = await _initialize_agent_system_components(
            websocket=websocket,
            session_id=session_id,  # type: ignore
            app_settings=app_settings,
            initial_state=initial_state,
            session_service=session_service,
            artifact_service=artifact_service,
            is_audio=is_audio == "true",
            notification_text=unquote(notification_text) if notification_text else "",
        )

        connect_and_run = get_connect_and_run_callable(
            websocket=websocket,
            live_events=live_events,
            live_request_queue=live_request_queue,
            notification_text=notification_text,
            artifact_service=artifact_service,
            session_id=session_id,
        )
        await connect_and_run()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.info(f"Error in websocket connection: {str(e)}")
        logger.info(f"Traceback: {traceback.format_exc()}")
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.send_json({"error": f"Internal server error: {str(e)}"})
        except Exception:
            pass

        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason=f"Internal server error: {str(e)}")
