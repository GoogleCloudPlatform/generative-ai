"""FastAPI application demonstrating ADK Gemini Live API Toolkit with WebSocket."""

import asyncio
import logging
import warnings
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.plugins.base_plugin import BasePlugin
from livekit_bridge import LiveKitSessionManager, LiveKitGeminiBridge

USE_LIVEKIT = os.getenv("USE_LIVEKIT", "false").lower() == "true"
USE_DATABASE_SESSION = os.getenv("USE_DATABASE_SESSION", "false").lower() == "true"

# Import agent after loading environment variables
# pylint: disable=wrong-import-position
from travel_booking import agent  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("debug2.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress Pydantic serialization warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Application name constant
APP_NAME = "livekit-adk"

# ========================================
# Phase 1: Application Initialization (once at startup)
# ========================================

app = FastAPI()

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount the session viewer app
from travel_booking.viewer_api import viewer_app
app.mount("/viewer", viewer_app)

# Define your session service
if USE_DATABASE_SESSION:
    from travel_booking.database_session_service import DatabaseSessionService
    session_service = DatabaseSessionService(db_path="sessions.db")
    logger.info("Using DatabaseSessionService (SQLite)")
else:
    session_service = InMemorySessionService()
    logger.info("Using InMemorySessionService")

class SessionResumptionIsolationPlugin(BasePlugin):
    """Plugin to clear live_session_resumption_handle during agent transitions.
    
    This avoids ValueErrors when sub-agents try to resume the parent agent's 
    session on non-Vertex key-based Gemini API.
    """
    def __init__(self):
        super().__init__(name="session_resumption_isolation")
        self.last_agent_name = None

    async def before_agent_callback(self, *, agent, callback_context):
        if self.last_agent_name is not None and self.last_agent_name != agent.name:
            logger.info(f"[Plugin] Clearing session resumption handle for transfer from {self.last_agent_name} to {agent.name}")
            callback_context._invocation_context.live_session_resumption_handle = None
        self.last_agent_name = agent.name
        return None

# Define your runner
runner = Runner(
    app_name=APP_NAME, 
    agent=agent.root_agent, 
    session_service=session_service,
    auto_create_session=True,
    plugins=[SessionResumptionIsolationPlugin()]
)

async def start_livekit_bridge_task(user_id: str, session_id: str):
    """Background task to run LiveKit bridge and ADK Runner."""
    logger.info(f"Starting LiveKit bridge task for user={user_id}, session={session_id}")
    
    session_manager = LiveKitSessionManager()
    try:
        # Use session_id as room name, and a descriptive participant name
        await session_manager.connect(room_name=session_id, participant_name="agent-bidi")
    except Exception as e:
        logger.error(f"Failed to connect agent to LiveKit: {e}")
        return
        
    # Ensure session exists in ADK session service BEFORE starting bridge task
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if not session:
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        logger.info(f"Created new ADK session: {session_id}")
        
    bridge = LiveKitGeminiBridge(session_manager.room, runner=runner, user_id=user_id, session_id=session_id)
    await bridge.start()
    
    # Configure for native audio model as recommended for LiveKit voice
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        session_resumption=None
    )

    try:
        # Keep the task alive while the bridge is running
        while bridge._running:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Error in LiveKit bridge task: {e}")
    finally:
        await bridge.stop()
        await session_manager.disconnect()
        logger.info(f"LiveKit bridge task finished for user={user_id}, session={session_id}")

# ========================================
# HTTP Endpoints
# ========================================


@app.get("/")
async def root():
    """Serve the index.html page."""
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/token")
async def get_token(user_id: str, session_id: str):
    """Generate LiveKit token for client."""
    if not USE_LIVEKIT:
        return {"error": "LiveKit is not enabled"}

    try:
        from livekit import api
    except ImportError:
        return {"error": "LiveKit SDK not installed on server"}

    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not all([url, api_key, api_secret]):
        return {"error": "LiveKit credentials not configured"}

    # Generate token
    grant = api.VideoGrants(room_join=True, room=session_id)
    token = api.AccessToken(api_key, api_secret).with_grants(grant).with_identity(user_id)

    # Start the bridge in the background so the agent joins the room
    logger.info(f"Kicking off LiveKit bridge task for room {session_id}")
    asyncio.create_task(start_livekit_bridge_task(user_id, session_id))

    return {"token": token.to_jwt(), "url": url}



