# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""GenMedia Live - Real-time multimodal AI creation application.

This application extends the Gemini Live API with image and video generation
capabilities using Gemini Pro Image and Veo through function calling.
"""

import asyncio
import base64
import logging
import os
import re
import threading
import traceback
from pathlib import Path

import google.auth
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from google import genai
from google.cloud import storage
from google.genai import types
from google.oauth2.credentials import Credentials

try:
    import io as pil_io

    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

app = Flask(__name__, static_folder="src", static_url_path="")
CORS(app)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    ping_timeout=300,
    ping_interval=60,
    max_http_buffer_size=50000000,
    transports=["polling"],
)

# Configuration
DEFAULT_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
DEFAULT_LOCATION_ID = "us-central1"

if not DEFAULT_PROJECT_ID:
    try:
        _, project = google.auth.default()
        if project:
            DEFAULT_PROJECT_ID = project
    except Exception:
        pass

VEO_MODEL_ID = "veo-3.1-generate-001"
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"
GEMINI_LIVE_MODEL = "gemini-live-2.5-flash-native-audio"

IMAGE_ASPECT_RATIOS = [
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
]
VIDEO_ASPECT_RATIOS = ["16:9", "9:16"]

# Initialize clients
try:
    default_gemini_client = genai.Client(
        vertexai=True, project=DEFAULT_PROJECT_ID, location=DEFAULT_LOCATION_ID
    )
    default_image_client = genai.Client(
        vertexai=True, project=DEFAULT_PROJECT_ID, location="global"
    )
    storage_client = storage.Client(project=DEFAULT_PROJECT_ID)
    logging.info(f"Initialized with project: {DEFAULT_PROJECT_ID}")
except Exception as e:
    logging.error(f"Initialization failed: {e}")
    default_gemini_client = None
    default_image_client = None

# Global state
session_credentials = {}
bridges = {}
live_sessions = {}
starting_sessions = set()
starting_session_sids = {}
session_states = {}
file_history = []
session_handles = {}
user_name = "User"
custom_system_instructions = ""


def sanitize_log(text, max_length=200):
    """Sanitize text for logging by removing base64 and image data."""
    if not text:
        return text
    text = str(text)
    text = re.sub(r"[A-Za-z0-9+/=]{50,}", "[base64]", text)
    text = re.sub(r"data:image/[^;]+;base64,[^\s,)]+", "[img]", text)
    return text[:max_length] + "..." if len(text) > max_length else text


def get_session_state(session_id):
    """Get or create session state for a given session ID."""
    if session_id not in session_states:
        session_states[session_id] = {
            "last_image": None,
            "last_video": None,
            "last_seen_frame": None,
            "uploaded_images": [],
        }
    return session_states[session_id]


def get_next_id_for_type(file_type, session_id):
    """Get the next available ID for a file type in a session."""
    existing = [
        e["id"]
        for e in file_history
        if e["type"] == file_type and e.get("session_id") == session_id
    ]
    return 1 if not existing else max(existing) + 1


def get_last_id_for_type(file_type, session_id):
    """Get the last ID for a file type in a session."""
    session_files = [
        f
        for f in file_history
        if f.get("session_id") == session_id and f.get("type") == file_type
    ]
    return max(f["id"] for f in session_files) if session_files else None


def get_active_client():
    """Get the active Gemini client using OAuth credentials."""
    if "oauth" not in session_credentials:
        return None
    creds_data = session_credentials["oauth"]
    creds = Credentials(token=creds_data["access_token"])
    return genai.Client(
        vertexai=True,
        project=creds_data["project_id"],
        location=creds_data["location"],
        credentials=creds,
    )


def get_active_image_client():
    """Get the active image generation client using OAuth credentials."""
    if "oauth" not in session_credentials:
        return None
    creds_data = session_credentials["oauth"]
    creds = Credentials(token=creds_data["access_token"])
    return genai.Client(
        vertexai=True,
        project=creds_data["project_id"],
        location="global",
        credentials=creds,
    )


def get_live_system_prompt(is_resumed=False):
    """Generate the system prompt for the Gemini Live API session."""
    custom = f"\n{custom_system_instructions}\n" if custom_system_instructions else ""
    name_section = (
        f"\nUser's name: {user_name}\n" if user_name and user_name != "User" else ""
    )
    resume_note = (
        "\nThis is a continued conversation. Continue naturally from where you left off.\n"
        if is_resumed
        else ""
    )

    return f"""You are GenMedia Live, a creative AI assistant with vision and media generation capabilities.
{custom}{name_section}{resume_note}

When the user asks you to SEE or DESCRIBE something (camera, uploaded image), just respond verbally - no tools needed.
When the user explicitly asks to GENERATE, CREATE, MAKE, or EDIT content, use the appropriate tool.

Available tools:
- generate_image: Create new images OR edit/modify existing ones by using them as reference
- generate_video: Create videos from text or animate images
- extract_frame: Get a frame from a video at a specific timestamp
- combine_videos: Merge multiple videos together
- view_generated_image: Load a previously generated image to see it

For image generation AND editing:
- To EDIT an existing image: set refers_to_last=true or use image_id to reference the image, then describe the changes in the prompt
- refers_to_camera=true: Use uploaded/camera image as reference
- refers_to_last=true: Use last generated image as reference for editing
- image_id: Reference a specific generated image by ID for editing

For video generation:
- Default duration is 8 seconds unless specified
- refers_to_last=true: Animate the last generated image
- image_id: Animate a specific image

Remember ALL conversation context and ALL previously generated content throughout the session.
Keep track of all generated images (image 1, image 2, etc.) and videos (video 1, video 2, etc.) by their IDs.
"""


class SessionBridge:
    """Bridge for communication between Flask and async Gemini Live session."""

    def __init__(self, loop):
        self.loop = loop
        self.queue = asyncio.Queue(maxsize=100)
        self.dropped_frames = 0

    def put_nowait(self, item):
        """Put an item in the queue from a non-async context."""
        if not self.loop.is_closed():
            try:
                self.loop.call_soon_threadsafe(self._safe_put, item)
            except RuntimeError:
                pass

    def _safe_put(self, item):
        """Safely put an item in the queue, dropping old items if full."""
        try:
            self.queue.put_nowait(item)
        except asyncio.QueueFull:
            self.dropped_frames += 1
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(item)
            except Exception:
                pass


async def run_live_session(session_id, sid):
    """Run the Gemini Live API session."""
    if session_id in live_sessions and live_sessions[session_id].get("active"):
        live_sessions[session_id]["sid"] = sid
        socketio.emit(
            "live_session_started",
            {"status": "reconnected", "user_name": user_name},
            room=sid,
        )
        return

    max_reconnects = 5
    reconnect_count = 0

    while reconnect_count < max_reconnects:
        resumption_handle = session_handles.get(session_id)
        is_resumed = resumption_handle is not None or reconnect_count > 0
        if resumption_handle:
            logging.info(f"Session {session_id}: resuming with handle")
        input_queue = asyncio.Queue(maxsize=100)

        loop = asyncio.get_event_loop()
        bridge = SessionBridge(loop)
        bridge.queue = input_queue
        bridges[session_id] = bridge

        try:
            tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name="generate_image",
                            description="Generate a new AI image OR edit/modify an existing image. For editing, use refers_to_last=true or image_id to reference the source image, and describe the desired changes in the prompt.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "prompt": {
                                        "type": "string",
                                        "description": "Description of the image to generate",
                                    },
                                    "aspect_ratio": {
                                        "type": "string",
                                        "enum": IMAGE_ASPECT_RATIOS,
                                    },
                                    "refers_to_camera": {
                                        "type": "boolean",
                                        "description": "Use camera/uploaded image as reference",
                                    },
                                    "refers_to_last": {
                                        "type": "boolean",
                                        "description": "Use last generated image as reference",
                                    },
                                    "image_id": {
                                        "type": "integer",
                                        "description": "Specific image ID to reference",
                                    },
                                },
                                "required": ["prompt"],
                            },
                        ),
                        types.FunctionDeclaration(
                            name="generate_video",
                            description="Generate a video from text or animate an image.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "prompt": {
                                        "type": "string",
                                        "description": "Description of video to generate",
                                    },
                                    "duration": {
                                        "type": "integer",
                                        "description": "Duration in seconds (4, 6, or 8)",
                                    },
                                    "refers_to_last": {
                                        "type": "boolean",
                                        "description": "Animate the last generated image",
                                    },
                                    "image_id": {
                                        "type": "integer",
                                        "description": "Specific image ID to animate",
                                    },
                                },
                                "required": ["prompt"],
                            },
                        ),
                        types.FunctionDeclaration(
                            name="extract_frame",
                            description="Extract a frame from a video at a specific timestamp",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "video_id": {
                                        "type": "integer",
                                        "description": "Video ID (defaults to last video)",
                                    },
                                    "timestamp": {
                                        "type": "number",
                                        "description": "Timestamp in seconds",
                                    },
                                },
                                "required": [],
                            },
                        ),
                        types.FunctionDeclaration(
                            name="combine_videos",
                            description="Combine multiple videos into one. Pass empty array to combine all session videos.",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "video_ids": {
                                        "type": "array",
                                        "items": {"type": "integer"},
                                        "description": "Video IDs to combine",
                                    },
                                },
                                "required": ["video_ids"],
                            },
                        ),
                        types.FunctionDeclaration(
                            name="view_generated_image",
                            description="Load a previously generated image to view it",
                            parameters={
                                "type": "object",
                                "properties": {
                                    "image_id": {
                                        "type": "integer",
                                        "description": "Image ID to view",
                                    },
                                },
                                "required": ["image_id"],
                            },
                        ),
                    ]
                )
            ]

            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                system_instruction=get_live_system_prompt(is_resumed=is_resumed),
                media_resolution=types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
                context_window_compression=types.ContextWindowCompressionConfig(
                    trigger_tokens=100000,
                    sliding_window=types.SlidingWindow(target_tokens=80000),
                ),
                session_resumption=types.SessionResumptionConfig(
                    handle=resumption_handle
                ),
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Aoede"
                        )
                    )
                ),
                tools=tools,
            )

            client = get_active_client()
            if client is None:
                current_sid = starting_session_sids.get(session_id, sid)
                socketio.emit(
                    "live_session_error",
                    {
                        "error": "Authentication required. Please enter your Project ID and access token.",
                        "code": 401,
                    },
                    room=current_sid,
                )
                starting_sessions.discard(session_id)
                return

            async with client.aio.live.connect(
                model=GEMINI_LIVE_MODEL, config=config
            ) as session:
                current_sid = starting_session_sids.get(session_id, sid)
                live_sessions[session_id] = {"active": True, "sid": current_sid}
                starting_sessions.discard(session_id)
                starting_session_sids.pop(session_id, None)
                socketio.emit(
                    "live_session_started",
                    {"status": "connected", "user_name": user_name},
                    room=current_sid,
                )

                async def sender_loop():
                    while live_sessions.get(session_id, {}).get("active"):
                        try:
                            item = await asyncio.wait_for(
                                input_queue.get(), timeout=0.5
                            )

                            if item["type"] == "audio":
                                await session.send_realtime_input(audio=item["data"])
                            elif item["type"] == "video":
                                await session.send_realtime_input(video=item["data"])
                            elif item["type"] == "text":
                                await session.send_client_content(
                                    turns=types.Content(
                                        role="user",
                                        parts=[types.Part(text=item["data"])],
                                    ),
                                    turn_complete=True,
                                )
                            elif item["type"] == "image_with_text":
                                for img_data in item.get("images", []):
                                    if isinstance(img_data, dict):
                                        blob = types.Blob(
                                            mime_type=img_data.get(
                                                "mime_type", "image/jpeg"
                                            ),
                                            data=img_data["data"],
                                        )
                                        for _ in range(5):
                                            await session.send_realtime_input(
                                                video=blob
                                            )
                                            await asyncio.sleep(0.1)
                                await session.send_client_content(
                                    turns=types.Content(
                                        role="user",
                                        parts=[
                                            types.Part(text=item.get("text", ""))
                                        ],
                                    ),
                                    turn_complete=True,
                                )
                            elif item["type"] == "image":
                                for img_data in item["data"]:
                                    if isinstance(img_data, dict):
                                        blob = types.Blob(
                                            mime_type=img_data.get(
                                                "mime_type", "image/jpeg"
                                            ),
                                            data=img_data["data"],
                                        )
                                        for _ in range(3):
                                            await session.send_realtime_input(
                                                video=blob
                                            )
                                            await asyncio.sleep(0.1)
                            elif item["type"] == "tool_response":
                                await session.send_tool_response(
                                    function_responses=item["data"]
                                )
                            elif item["type"] == "generated_image_feedback":
                                img_data = item["data"]
                                blob = types.Blob(
                                    mime_type=img_data.get("mime_type", "image/png"),
                                    data=img_data["data"],
                                )
                                await session.send_client_content(
                                    turns=types.Content(
                                        role="user",
                                        parts=[
                                            types.Part(inline_data=blob),
                                            types.Part(
                                                text=f"[Generated image {item.get('id', '?')}]"
                                            ),
                                        ],
                                    ),
                                    turn_complete=False,
                                )
                            input_queue.task_done()
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            logging.error(f"Send error: {e}")

                async def receiver_loop():
                    try:
                        while live_sessions.get(session_id, {}).get("active"):
                            async for response in session.receive():
                                if not live_sessions.get(session_id, {}).get("active"):
                                    return "ended"
                                current_sid = live_sessions[session_id]["sid"]

                                if response.session_resumption_update:
                                    update = response.session_resumption_update
                                    if update.resumable and update.new_handle:
                                        session_handles[session_id] = update.new_handle
                                        logging.info(
                                            f"Session {session_id}: captured resumption handle"
                                        )

                                if response.tool_call:
                                    for fc in response.tool_call.function_calls:
                                        socketio.emit(
                                            "voice_generation_request",
                                            {
                                                "text": "Generating...",
                                                "function_name": fc.name,
                                                "function_args": dict(fc.args),
                                                "function_call_id": fc.id,
                                            },
                                            room=current_sid,
                                        )

                                if (
                                    response.server_content
                                    and response.server_content.model_turn
                                ):
                                    for (
                                        part
                                    ) in response.server_content.model_turn.parts:
                                        if part.text:
                                            socketio.emit(
                                                "text_response",
                                                {"text": part.text},
                                                room=current_sid,
                                            )
                                        if part.inline_data:
                                            audio_b64 = base64.b64encode(
                                                part.inline_data.data
                                            ).decode("utf-8")
                                            socketio.emit(
                                                "audio_response",
                                                {
                                                    "audio": audio_b64,
                                                    "mime_type": part.inline_data.mime_type,
                                                },
                                                room=current_sid,
                                            )
                    except asyncio.CancelledError:
                        return "cancelled"
                    except Exception as e:
                        error_msg = str(e)
                        if (
                            "1011" in error_msg
                            or "Insufficient model resources" in error_msg
                        ):
                            current_sid = live_sessions[session_id]["sid"]
                            socketio.emit(
                                "live_session_error",
                                {
                                    "error": "Server overloaded. Please try again.",
                                    "code": 1011,
                                },
                                room=current_sid,
                            )
                            return "capacity_error"
                        if "1000" in error_msg or "cancelled" in error_msg.lower():
                            return "reconnect"
                        logging.error(f"Receive error: {e}")
                        return "error"
                    return "ended"

                sender_task = asyncio.create_task(sender_loop())
                receiver_task = asyncio.create_task(receiver_loop())

                done, pending = await asyncio.wait(
                    [sender_task, receiver_task], return_when=asyncio.FIRST_COMPLETED
                )

                session_active = live_sessions.get(session_id, {}).get("active", False)
                should_reconnect = False
                for task in done:
                    try:
                        result = task.result()
                        if result == "reconnect":
                            should_reconnect = True
                        elif result == "ended" and session_active:
                            should_reconnect = True
                    except Exception:
                        pass

                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                session_state = get_session_state(session_id)
                session_state["should_reconnect"] = should_reconnect

            session_active = live_sessions.get(session_id, {}).get("active", False)
            should_reconnect = get_session_state(session_id).get(
                "should_reconnect", False
            )
            has_handle = session_id in session_handles

            if session_active and (should_reconnect or has_handle):
                reconnect_count += 1
                logging.info(
                    f"Reconnecting session {session_id} (attempt {reconnect_count}, has_handle={has_handle})"
                )
                await asyncio.sleep(1)
                continue
            else:
                break

        except Exception as e:
            logging.error(f"Session error: {e}")
            current_sid = live_sessions.get(session_id, {}).get("sid", sid)
            error_msg = str(e)

            if "1011" in error_msg or "Insufficient model resources" in error_msg:
                socketio.emit(
                    "live_session_error",
                    {
                        "error": "Server overloaded. Please try again.",
                        "code": 1011,
                    },
                    room=current_sid,
                )
                break

            socketio.emit(
                "live_session_error", {"error": str(e)}, room=current_sid
            )

            if (
                "1000" in error_msg or "cancelled" in error_msg.lower()
            ) and reconnect_count < max_reconnects:
                reconnect_count += 1
                await asyncio.sleep(2)
                continue
            else:
                break

    if session_id in bridges:
        del bridges[session_id]
    if session_id in live_sessions:
        final_sid = live_sessions[session_id]["sid"]
        del live_sessions[session_id]
        socketio.emit(
            "session_ended_reconnect",
            {"session_id": session_id, "can_resume": session_id in session_handles},
            room=final_sid,
        )
    starting_sessions.discard(session_id)


def start_background_loop(session_id, sid):
    """Start the async event loop for the Gemini Live session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_live_session(session_id, sid))
    except Exception as e:
        logging.error(f"Loop error: {e}")
    finally:
        starting_sessions.discard(session_id)
        loop.close()


# Socket handlers
@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logging.info(f"Client connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logging.info(f"Client disconnected: {request.sid}")


@socketio.on("start_live_session")
def handle_start(data):
    """Handle start live session request."""
    session_id = data.get("session_id", "default")
    sid = request.sid

    session_state = get_session_state(session_id)
    session_state["uploaded_images"] = []
    session_state["last_seen_frame"] = None

    if session_id in bridges and session_id in live_sessions:
        live_sessions[session_id]["sid"] = sid
        emit("live_session_started", {"status": "reconnected", "user_name": user_name})
        return

    if session_id in starting_sessions:
        starting_session_sids[session_id] = sid
        return

    starting_sessions.add(session_id)
    starting_session_sids[session_id] = sid
    t = threading.Thread(
        target=start_background_loop, args=(session_id, sid), daemon=True
    )
    t.start()


@socketio.on("stop_live_session")
def handle_stop(data):
    """Handle stop live session request."""
    session_id = data.get("session_id")
    if session_id in live_sessions:
        live_sessions[session_id]["active"] = False
        emit("live_session_stopped")


@socketio.on("check_session_status")
def handle_check_session(data):
    """Check if a session is active."""
    session_id = data.get("session_id")
    sid = request.sid

    if session_id in bridges and session_id in live_sessions:
        live_sessions[session_id]["sid"] = sid
        emit("live_session_started", {"status": "reconnected", "user_name": user_name})
        return {"active": True}
    elif session_id in starting_sessions:
        starting_session_sids[session_id] = sid
        return {"active": False, "starting": True}
    return {"active": False}


@socketio.on("send_audio")
def handle_audio(data):
    """Handle incoming audio data."""
    session_id = data.get("session_id")
    audio = data.get("audio")

    if not session_id or session_id not in bridges or not audio:
        return

    try:
        import struct

        if isinstance(audio, list):
            b = struct.pack(f"<{len(audio)}h", *audio)
        else:
            b = base64.b64decode(audio)
        audio_blob = types.Blob(mime_type="audio/pcm;rate=16000", data=b)
        bridges[session_id].put_nowait({"type": "audio", "data": audio_blob})
    except Exception as e:
        logging.error(f"Audio error: {e}")


@socketio.on("send_camera_frame")
def handle_video(data):
    """Handle incoming camera frame."""
    session_id = data.get("session_id")
    frame = data.get("frame")

    if session_id and frame:
        get_session_state(session_id)[
            "last_seen_frame"
        ] = f"data:image/jpeg;base64,{frame}"

    if session_id in bridges and frame:
        try:
            frame_bytes = base64.b64decode(frame)
            video_blob = types.Blob(mime_type="image/jpeg", data=frame_bytes)
            bridges[session_id].put_nowait({"type": "video", "data": video_blob})
        except Exception as e:
            logging.error(f"Frame error: {e}")


@socketio.on("send_text_message")
def handle_text(data):
    """Handle incoming text message."""
    session_id = data.get("session_id")
    text = data.get("text")
    if session_id in bridges and text:
        bridges[session_id].put_nowait({"type": "text", "data": text})


@socketio.on("send_uploaded_images")
def handle_uploaded_images(data):
    """Handle uploaded images."""
    session_id = data.get("session_id")
    images = data.get("images", [])

    if not session_id or not images:
        return {"status": "error", "message": "No session_id or images"}

    session_state = get_session_state(session_id)
    session_state["uploaded_images"] = images
    if images:
        session_state["last_seen_frame"] = images[-1]

    if session_id in bridges and session_id in live_sessions:
        try:
            processed_images = []
            for img_data_url in images:
                if isinstance(img_data_url, str) and "," in img_data_url:
                    header, b64_data = img_data_url.split(",", 1)
                    img_bytes = base64.b64decode(b64_data)

                    if PIL_AVAILABLE:
                        img = Image.open(pil_io.BytesIO(img_bytes))
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.thumbnail((768, 768), Image.Resampling.LANCZOS)
                        canvas = Image.new("RGB", (768, 768), (128, 128, 128))
                        x = (768 - img.width) // 2
                        y = (768 - img.height) // 2
                        canvas.paste(img, (x, y))
                        buffer = pil_io.BytesIO()
                        canvas.save(buffer, format="JPEG", quality=85)
                        processed_images.append(
                            {"mime_type": "image/jpeg", "data": buffer.getvalue()}
                        )
                    else:
                        mime_type = "image/jpeg" if "jpeg" in header else "image/png"
                        processed_images.append(
                            {"mime_type": mime_type, "data": img_bytes}
                        )

            if processed_images:
                bridges[session_id].put_nowait(
                    {"type": "image", "data": processed_images}
                )
                return {"status": "ok", "queued": len(processed_images)}
        except Exception as e:
            logging.error(f"Image upload error: {e}")
            return {"status": "error", "message": str(e)}
    return {"status": "stored"}


@socketio.on("send_message_with_images")
def handle_message_with_images(data):
    """Handle text message with images."""
    session_id = data.get("session_id")
    text = data.get("text", "")
    images = data.get("images", [])

    if not session_id or session_id not in bridges:
        return {"status": "error", "message": "Session not active"}

    session_state = get_session_state(session_id)
    session_state["uploaded_images"] = images
    if images:
        session_state["last_seen_frame"] = images[-1]

    try:
        processed_images = []
        for img_data_url in images:
            if isinstance(img_data_url, str) and "," in img_data_url:
                header, b64_data = img_data_url.split(",", 1)
                img_bytes = base64.b64decode(b64_data)
                mime_type = "image/jpeg"
                if "image/png" in header:
                    mime_type = "image/png"

                if PIL_AVAILABLE:
                    img = Image.open(pil_io.BytesIO(img_bytes))
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.thumbnail((768, 768), Image.Resampling.LANCZOS)
                    canvas = Image.new("RGB", (768, 768), (128, 128, 128))
                    x = (768 - img.width) // 2
                    y = (768 - img.height) // 2
                    canvas.paste(img, (x, y))
                    buffer = pil_io.BytesIO()
                    canvas.save(buffer, format="JPEG", quality=85)
                    processed_images.append(
                        {"mime_type": "image/jpeg", "data": buffer.getvalue()}
                    )
                else:
                    processed_images.append({"mime_type": mime_type, "data": img_bytes})

        context = f"[User uploaded {len(images)} image(s)]: {text}" if images else text
        bridges[session_id].put_nowait(
            {"type": "image_with_text", "images": processed_images, "text": context}
        )
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Message with images error: {e}")
        return {"status": "error", "message": str(e)}


@socketio.on("generation_completed")
def handle_gen_complete(data):
    """Handle generation completed notification."""
    session_id = data.get("session_id")
    gen_id = data.get("id")
    gen_type = data.get("type")
    call_id = data.get("function_call_id")

    if session_id in bridges and call_id:
        response = [
            types.FunctionResponse(
                id=call_id,
                name="generate_content",
                response={"status": "completed", "result": f"Generated {gen_type} {gen_id}"},
            )
        ]
        bridges[session_id].put_nowait({"type": "tool_response", "data": response})

        if gen_type == "image":
            try:
                img_path = Path(f"outputs/images/image_{gen_id}.png")
                if img_path.exists():
                    img_bytes = img_path.read_bytes()
                    bridges[session_id].put_nowait(
                        {
                            "type": "generated_image_feedback",
                            "data": {"mime_type": "image/png", "data": img_bytes},
                            "id": gen_id,
                        }
                    )
            except Exception as e:
                logging.error(f"Error sending generated image: {e}")


# REST API routes
@app.route("/api/genmedia-chat", methods=["POST"])
def handle_genmedia_chat():
    """Handle generation requests from the frontend."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data received"}), 400

        session_id = data.get("session_id", "default")

        tool_name = data.get("function_name") or data.get("tool") or data.get("name")
        tool_decision = data.get("tool_decision") or {}
        if isinstance(tool_decision, dict):
            tool_name = tool_name or tool_decision.get(
                "function_name"
            ) or tool_decision.get("tool")

        args = {}
        if data.get("function_args") and isinstance(data.get("function_args"), dict):
            args = data.get("function_args")
        elif tool_decision.get("function_args") and isinstance(
            tool_decision.get("function_args"), dict
        ):
            args = tool_decision.get("function_args")

        if not tool_name:
            return jsonify({"error": "No tool name found"}), 400

        if tool_name in ["nano_banana", "generate_image"]:
            return handle_image_generation(args, session_id)
        elif tool_name in ["veo", "generate_video"]:
            return handle_video_generation(args, session_id)
        elif tool_name == "extract_frame":
            video_id = args.get("video_id") or get_last_id_for_type("video", session_id)
            if video_id is None:
                return jsonify({"error": "No videos found"}), 404
            return handle_extract_frame(
                {"video_id": video_id, "timestamp": args.get("timestamp", 0)},
                session_id,
            )
        elif tool_name == "combine_videos":
            video_ids = args.get("video_ids", [])
            if len(video_ids) < 2:
                session_videos = [
                    f
                    for f in file_history
                    if f.get("session_id") == session_id and f.get("type") == "video"
                ]
                video_ids = sorted([f["id"] for f in session_videos])
            if len(video_ids) < 2:
                return jsonify({"error": "Need at least 2 videos"}), 400
            return handle_combine_videos({"video_ids": video_ids}, session_id)
        elif tool_name == "view_generated_image":
            image_id = args.get("image_id")
            if image_id is None:
                return jsonify({"error": "No image_id provided"}), 400
            img_path = Path(f"outputs/images/image_{image_id}.png")
            if not img_path.exists():
                return jsonify({"error": f"Image {image_id} not found"}), 404
            if session_id in bridges:
                bridges[session_id].put_nowait(
                    {
                        "type": "generated_image_feedback",
                        "data": {"mime_type": "image/png", "data": img_path.read_bytes()},
                        "id": image_id,
                    }
                )
            return jsonify({"response": f"Image {image_id} loaded", "image_id": image_id})

        return jsonify({"response": "Unknown tool", "tool": tool_name})
    except Exception as e:
        logging.error(f"API error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def handle_image_generation(args, session_id):
    """Handle image generation requests."""
    session_state = get_session_state(session_id)
    prompt = args.get("prompt")
    aspect_ratio = args.get("aspect_ratio", args.get("aspectRatio", "1:1"))
    if aspect_ratio not in IMAGE_ASPECT_RATIOS:
        aspect_ratio = "1:1"

    ref_images = args.get("reference_images", [])
    refers_to_camera = args.get("refers_to_camera", False)
    refers_to_last = args.get("refers_to_last", False)
    specific_image_id = args.get("image_id")
    if specific_image_id is not None:
        specific_image_id = int(specific_image_id)

    if refers_to_camera:
        if session_state.get("uploaded_images"):
            ref_images.extend(session_state.get("uploaded_images"))
        elif session_state.get("last_seen_frame"):
            ref_images.append(session_state.get("last_seen_frame"))

    if specific_image_id:
        session_images = [
            f
            for f in file_history
            if f.get("session_id") == session_id and f.get("type") == "image"
        ]
        matching = [f for f in session_images if f.get("id") == specific_image_id]
        if matching:
            img_path = Path(matching[0]["path"])
            if img_path.exists():
                with open(img_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")
                    ref_images.append(f"data:image/png;base64,{img_data}")

    if refers_to_last and not specific_image_id:
        last_id = get_last_id_for_type("image", session_id)
        if last_id:
            img_path = Path(f"outputs/images/image_{last_id}.png")
            if img_path.exists():
                with open(img_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")
                    ref_images.append(f"data:image/png;base64,{img_data}")

    try:
        generation_config = types.GenerateContentConfig(
            temperature=0.7,
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size="2K"),
        )

        content_parts = []
        for ref_img in ref_images[:4]:
            if isinstance(ref_img, str) and ref_img.startswith("data:"):
                try:
                    b = base64.b64decode(ref_img.split(",")[1])
                    content_parts.append(
                        {"inline_data": {"mime_type": "image/png", "data": b}}
                    )
                except Exception:
                    pass

        if content_parts:
            content_parts.append(f"Based on the reference image(s), create: {prompt}")
        else:
            content_parts.append(prompt)

        client = get_active_image_client()
        if client is None:
            return (
                jsonify(
                    {
                        "error": "Authentication required. Please enter your Project ID and access token."
                    }
                ),
                401,
            )
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL, contents=content_parts, config=generation_config
        )

        output_dir = Path("outputs/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        next_id = get_next_id_for_type("image", session_id)
        image_path = output_dir / f"image_{next_id}.png"

        image_saved = False
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.inline_data:
                        image_path.write_bytes(part.inline_data.data)
                        image_saved = True
                        break

        if not image_saved:
            return jsonify({"error": "No image generated"}), 500

        session_state["last_image"] = str(image_path)
        file_history.append(
            {"id": next_id, "type": "image", "path": str(image_path), "session_id": session_id}
        )

        return jsonify(
            {
                "response": f"Generated image {next_id}",
                "file": {
                    "id": next_id,
                    "type": "image",
                    "url": f"/outputs/images/image_{next_id}.png",
                },
            }
        )
    except Exception as e:
        logging.error(f"Image generation error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def handle_video_generation(args, session_id):
    """Handle video generation requests."""
    import time

    session_state = get_session_state(session_id)
    prompt = args.get("prompt", "")
    duration = args.get("duration", 8)
    refers_to_last = args.get("refers_to_last", False)
    image_id = args.get("image_id")
    if image_id is not None:
        image_id = int(image_id)

    if duration <= 4:
        duration = 4
    elif duration <= 6:
        duration = 6
    else:
        duration = 8

    try:
        reference_image = None

        if image_id:
            img_path = Path(f"outputs/images/image_{image_id}.png")
            if img_path.exists():
                reference_image = img_path
        elif refers_to_last:
            last_id = get_last_id_for_type("image", session_id)
            if last_id:
                img_path = Path(f"outputs/images/image_{last_id}.png")
                if img_path.exists():
                    reference_image = img_path

        if "oauth" not in session_credentials:
            return (
                jsonify(
                    {
                        "error": "Authentication required. Please enter your Project ID and access token."
                    }
                ),
                401,
            )
        creds_data = session_credentials["oauth"]
        creds = Credentials(token=creds_data["access_token"])
        video_client = genai.Client(
            vertexai=True,
            project=creds_data["project_id"],
            location="global",
            credentials=creds,
        )

        output_dir = Path("outputs/videos")
        output_dir.mkdir(parents=True, exist_ok=True)
        next_id = get_next_id_for_type("video", session_id)
        video_path = output_dir / f"video_{next_id}.mp4"

        video_config = types.GenerateVideosConfig(
            aspect_ratio="16:9",
            number_of_videos=1,
            duration_seconds=duration,
            enhance_prompt=True,
            person_generation="allow_adults",
        )

        if reference_image and reference_image.exists():
            operation = video_client.models.generate_videos(
                model=VEO_MODEL_ID,
                prompt=prompt,
                image=types.Image(
                    image_bytes=reference_image.read_bytes(), mime_type="image/png"
                ),
                config=video_config,
            )
        else:
            operation = video_client.models.generate_videos(
                model=VEO_MODEL_ID,
                prompt=prompt,
                config=video_config,
            )

        max_wait = 300
        waited = 0
        while not operation.done and waited < max_wait:
            time.sleep(15)
            waited += 15
            operation = video_client.operations.get(operation)

        if not operation.done:
            return jsonify({"error": "Video generation timed out"}), 500

        result = operation.result if hasattr(operation, "result") else operation.response
        if not result or not result.generated_videos:
            return jsonify({"error": "No video generated"}), 500

        video = result.generated_videos[0].video

        if hasattr(video, "video_bytes") and video.video_bytes:
            video_path.write_bytes(video.video_bytes)
        elif hasattr(video, "uri") and video.uri:
            gcs_match = re.match(r"gs://([^/]+)/(.+)", video.uri)
            if gcs_match:
                bucket_name, blob_name = gcs_match.groups()
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                blob.download_to_filename(str(video_path))
            else:
                return jsonify({"error": "Invalid video URI"}), 500
        else:
            return jsonify({"error": "No video data available"}), 500

        session_state["last_video"] = str(video_path)
        file_history.append(
            {"id": next_id, "type": "video", "path": str(video_path), "session_id": session_id}
        )

        return jsonify(
            {
                "response": f"Generated video {next_id}",
                "file": {
                    "id": next_id,
                    "type": "video",
                    "url": f"/outputs/videos/video_{next_id}.mp4",
                },
            }
        )

    except Exception as e:
        logging.error(f"Video generation error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def handle_extract_frame(args, session_id):
    """Handle frame extraction from video."""
    import subprocess

    video_id = args.get("video_id", 1)
    if video_id is not None:
        video_id = int(video_id)
    timestamp = args.get("timestamp", 0)

    try:
        video_path = Path(f"outputs/videos/video_{video_id}.mp4")
        if not video_path.exists():
            for f in file_history:
                if f.get("type") == "video" and f.get("id") == video_id:
                    video_path = Path(f["path"])
                    break

        if not video_path.exists():
            return jsonify({"error": f"Video {video_id} not found"}), 404

        output_dir = Path("outputs/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        next_id = get_next_id_for_type("image", session_id)
        frame_path = output_dir / f"image_{next_id}.png"

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            str(video_path),
            "-vframes",
            "1",
            "-f",
            "image2",
            "-vcodec",
            "png",
            str(frame_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 or not frame_path.exists():
            return jsonify({"error": "Frame extraction failed"}), 500

        session_state = get_session_state(session_id)
        session_state["last_image"] = str(frame_path)
        file_history.append(
            {"id": next_id, "type": "image", "path": str(frame_path), "session_id": session_id}
        )

        return jsonify(
            {
                "response": f"Extracted frame {next_id} from video {video_id}",
                "file": {
                    "id": next_id,
                    "type": "image",
                    "url": f"/outputs/images/image_{next_id}.png",
                },
            }
        )

    except Exception as e:
        logging.error(f"Frame extraction error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def handle_combine_videos(args, session_id):
    """Handle combining multiple videos."""
    import subprocess
    import tempfile

    video_ids = args.get("video_ids", [])
    video_ids = [int(v) for v in video_ids]

    if len(video_ids) < 2:
        return jsonify({"error": "Need at least 2 videos"}), 400

    try:
        video_paths = []
        for vid_id in video_ids:
            video_path = Path(f"outputs/videos/video_{vid_id}.mp4")
            if not video_path.exists():
                for f in file_history:
                    if f.get("type") == "video" and f.get("id") == vid_id:
                        video_path = Path(f["path"])
                        break
            if not video_path.exists():
                return jsonify({"error": f"Video {vid_id} not found"}), 404
            video_paths.append(video_path)

        output_dir = Path("outputs/videos")
        output_dir.mkdir(parents=True, exist_ok=True)
        next_id = get_next_id_for_type("video", session_id)
        output_path = output_dir / f"video_{next_id}.mp4"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            concat_file = f.name
            for vp in video_paths:
                f.write(f"file '{vp.absolute()}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
            "-c",
            "copy",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        Path(concat_file).unlink(missing_ok=True)

        if result.returncode != 0:
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_file,
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-preset",
                "fast",
                str(output_path),
            ]
            subprocess.run(cmd, capture_output=True, text=True)

        if not output_path.exists():
            return jsonify({"error": "Video combination failed"}), 500

        session_state = get_session_state(session_id)
        session_state["last_video"] = str(output_path)
        file_history.append(
            {"id": next_id, "type": "video", "path": str(output_path), "session_id": session_id}
        )

        return jsonify(
            {
                "response": f"Combined {len(video_ids)} videos into video {next_id}",
                "file": {
                    "id": next_id,
                    "type": "video",
                    "url": f"/outputs/videos/video_{next_id}.mp4",
                },
            }
        )

    except Exception as e:
        logging.error(f"Video combination error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/validate-token", methods=["POST"])
def validate_token():
    """Validate user's access token."""
    global session_credentials
    data = request.json
    project_id = data.get("projectId")
    location = data.get("location", "us-central1")
    access_token = data.get("accessToken")

    if not project_id or not access_token:
        return jsonify({"valid": False, "message": "Project ID and token required"})

    try:
        creds = Credentials(token=access_token)

        test_client = genai.Client(
            vertexai=True, project=project_id, location=location, credentials=creds
        )

        test_client.models.generate_content(
            model="gemini-2.0-flash", contents="Say 'ok' and nothing else"
        )

        session_credentials["oauth"] = {
            "credentials": creds,
            "project_id": project_id,
            "location": location,
            "access_token": access_token,
        }

        logging.info(f"User authenticated with project: {project_id}")
        return jsonify({"valid": True, "project": project_id})
    except Exception as e:
        logging.error(f"Token validation failed: {e}")
        return jsonify({"valid": False, "message": str(e)})


@app.route("/api/auth-status", methods=["GET"])
def auth_status():
    """Get current authentication status."""
    if "oauth" in session_credentials:
        return jsonify(
            {"authenticated": True, "project": session_credentials["oauth"]["project_id"]}
        )
    return jsonify(
        {"authenticated": False, "project": DEFAULT_PROJECT_ID, "using": "default"}
    )


@app.route("/api/logout", methods=["POST"])
def logout():
    """Log out the current user."""
    global session_credentials
    if "oauth" in session_credentials:
        del session_credentials["oauth"]
        logging.info("User logged out, using default credentials")
    return jsonify({"success": True})


@app.route("/api/set-user-name", methods=["POST"])
def set_user_name_route():
    """Set the user's display name."""
    global user_name
    user_name = request.json.get("name", "User")
    return jsonify({"success": True, "name": user_name})


@app.route("/api/get-user-name", methods=["GET"])
def get_user_name_route():
    """Get the user's display name."""
    return jsonify({"name": user_name})


@app.route("/api/get-system-instructions", methods=["GET"])
def get_system_instructions():
    """Get custom system instructions."""
    return jsonify({"instructions": custom_system_instructions})


@app.route("/api/set-system-instructions", methods=["POST"])
def set_system_instructions():
    """Set custom system instructions."""
    global custom_system_instructions
    custom_system_instructions = request.json.get("instructions", "").strip()
    return jsonify({"success": True, "instructions": custom_system_instructions})


@app.route("/api/clear-all", methods=["POST"])
def clear_all():
    """Clear all session data."""
    global file_history
    session_id = request.json.get("session_id", "default")
    if session_id in session_states:
        del session_states[session_id]
    if session_id in session_handles:
        del session_handles[session_id]
    file_history = [f for f in file_history if f.get("session_id") != session_id]
    return jsonify({"success": True})


@app.route("/api/list-files", methods=["GET"])
def api_list_files():
    """List all files for a session."""
    session_id = request.args.get("session_id", "default")
    files = [f for f in file_history if f.get("session_id") == session_id]
    return jsonify({"files": files})


@app.route("/")
def serve_home():
    """Serve the main page."""
    return send_from_directory(".", "index.html")


@app.route("/outputs/<path:filename>")
def serve_output(filename):
    """Serve generated output files."""
    return send_from_directory("outputs", filename)


@app.route("/src/<path:filename>")
def serve_src_files(filename):
    """Serve source files."""
    return send_from_directory("src", filename)


@app.route("/style.css")
def serve_style():
    """Serve the stylesheet."""
    if Path("style.css").exists():
        return send_from_directory(".", "style.css")
    return "", 200


if __name__ == "__main__":
    import shutil

    print("=" * 50)
    print("GenMedia Live")
    print(f"Project: {DEFAULT_PROJECT_ID}")
    print(f"ffmpeg: {'available' if shutil.which('ffmpeg') else 'NOT FOUND'}")
    print("=" * 50)

    socketio.run(app, host="0.0.0.0", port=8080, debug=False)