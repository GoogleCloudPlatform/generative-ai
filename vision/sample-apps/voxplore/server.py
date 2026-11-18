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

import asyncio
import base64
import json
import logging
import mimetypes
import os
import ssl
import sys
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import certifi
import websockets
from dotenv import load_dotenv
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Response

# before importing the agent package, which reads the environment at import time
load_dotenv()

from voxplore import (  # noqa: E402
    AVATARS,
    VOICES,
    ClientMessage,
    ServerMessage,
    SessionState,
    SetupMessage,
    add_upload,
    app_name,
    default_avatar,
    default_voice,
    get_agent_setup_config,
    handle_scene_event,
    load_paper,
    preset,
    proactive_default,
    remove_upload,
    root_agent,
    run_function_call,
    set_mode,
)
from voxplore.auth import get_access_token  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("adk_live_backend")

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


def get_service_url() -> str:
    override_url = os.environ.get("GEMINI_LIVE_API_URL")
    if override_url:
        return override_url
    region = os.environ.get("GCP_REGION", "us-central1")
    host = (
        "aiplatform.googleapis.com"
        if region == "global"
        else f"{region}-aiplatform.googleapis.com"
    )
    return (
        f"wss://{host}/ws/google.cloud.aiplatform.v1.LlmBidiService/BidiGenerateContent"
    )


SERVICE_URL = get_service_url()
API_KEY = os.environ.get("GEMINI_API_KEY", "")


def uses_api_key() -> bool:
    return bool(API_KEY) and "generativelanguage.googleapis.com" in SERVICE_URL


def get_vertex_url() -> str:
    if uses_api_key():
        return f"{SERVICE_URL}?key={API_KEY}"
    return SERVICE_URL


def get_vertex_headers() -> dict:
    if uses_api_key():
        return {}
    return {"Authorization": f"Bearer {get_access_token()}"}


def get_ssl_context() -> ssl.SSLContext:
    try:
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def log_server_message(parsed: ServerMessage, raw_message: str = ""):
    if parsed.error:
        logger.error(
            f"Live API error: Code={parsed.error.code}, Status={parsed.error.status}, "
            f"Message='{parsed.error.message}', Raw={raw_message}"
        )
    if parsed.setup_complete:
        logger.info("Live API session setup completed.")
    if parsed.usage_metadata:
        u = parsed.usage_metadata
        logger.info(
            f"Usage Metadata: Input={u.prompt_token_count or 0}, "
            f"Output={u.response_token_count or 0}, "
            f"Thoughts={u.thoughts_token_count or 0}, "
            f"Total={u.total_token_count or 0} tokens"
        )
    content = parsed.server_content
    if not content:
        if not (
            parsed.error
            or parsed.setup_complete
            or parsed.usage_metadata
            or parsed.tool_call
            or parsed.tool_call_cancellation
        ):
            logger.info(f"Live API raw message: {raw_message}")
        return
    if content.interrupted:
        logger.warning("Model interrupted by user input.")
    if content.input_transcription and content.input_transcription.text:
        logger.info(f"User Spoke: {content.input_transcription.text}")
    if content.output_transcription and content.output_transcription.text:
        logger.info(f"Model Spoke: {content.output_transcription.text}")
    if content.model_turn and content.model_turn.parts:
        for part in content.model_turn.parts:
            if part.text:
                logger.info(f"Model Response Text: {part.text}")


async def proxy_bidirectional(client_ws: Any, vertex_ws: Any):
    """Bidirectional proxy between the browser and the Live API."""
    state = SessionState()
    background_tasks: set[asyncio.Task] = set()
    ready = asyncio.Event()

    def spawn(coro):
        task = asyncio.create_task(coro)
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    async def client_to_vertex():
        audio_chunks = 0
        video_frames = 0
        try:
            async for message in client_ws:
                try:
                    parsed = ClientMessage.model_validate_json(message)
                    if not ready.is_set():
                        # the Live API rejects input until it confirms the setup
                        realtime = parsed.realtime_input
                        if realtime and (realtime.audio or realtime.video):
                            if realtime.video:
                                state.last_frame = (
                                    realtime.video.mime_type,
                                    base64.b64decode(realtime.video.data),
                                )
                            continue
                        await ready.wait()
                    if parsed.scene_event:
                        # from an interactive scene in the browser, handled here and not forwarded
                        spawn(
                            handle_scene_event(
                                parsed.scene_event, state, client_ws, vertex_ws
                            )
                        )
                        continue
                    if parsed.paper_request:
                        spawn(
                            load_paper(
                                parsed.paper_request, state, client_ws, vertex_ws
                            )
                        )
                        continue
                    if parsed.upload_request:
                        await add_upload(parsed.upload_request, state, vertex_ws)
                        continue
                    if parsed.mode_request:
                        await set_mode(parsed.mode_request, vertex_ws)
                        continue
                    if parsed.upload_remove:
                        await remove_upload(parsed.upload_remove, state, vertex_ws)
                        continue
                    realtime = parsed.realtime_input
                    if realtime and realtime.text:
                        logger.info(f"User Query: {realtime.text}")
                    if realtime and realtime.audio:
                        audio_chunks += 1
                        if audio_chunks == 1 or audio_chunks % 100 == 0:
                            blob = realtime.audio
                            logger.info(
                                f"Forwarding audio chunk {audio_chunks} ({blob.mime_type}, {len(blob.data)} base64 chars)"
                            )
                    if realtime and realtime.video:
                        state.last_frame = (
                            realtime.video.mime_type,
                            base64.b64decode(realtime.video.data),
                        )
                        video_frames += 1
                        if video_frames == 1 or video_frames % 30 == 0:
                            logger.info(
                                f"Forwarding video frame {video_frames} ({realtime.video.mime_type}, {len(realtime.video.data)} base64 chars)"
                            )
                    await vertex_ws.send(
                        parsed.model_dump_json(by_alias=True, exclude_none=True)
                    )
                except Exception as e:
                    logger.error(f"Error parsing or forwarding client message: {e}")
                    if ready.is_set():
                        await vertex_ws.send(message)
        except ConnectionClosed:
            logger.info("Client disconnected.")
        except Exception as e:
            logger.error(f"Error in client_to_vertex: {e}")

    async def vertex_to_client():
        try:
            async for message in vertex_ws:
                # forward first, parse after, so logging never delays the stream
                if isinstance(message, bytes):
                    try:
                        message = message.decode("utf-8")
                    except UnicodeDecodeError:
                        logger.info(
                            f"Received binary non-UTF8 frame from the Live API ({len(message)} bytes)"
                        )
                        await client_ws.send(message)
                        continue
                await client_ws.send(message)

                # video chunks are large, skip parsing them unless they contain usageMetadata or toolCall
                if (
                    len(message) >= 10000
                    and "usageMetadata" not in message
                    and "toolCall" not in message
                ):
                    continue
                try:
                    parsed = ServerMessage.model_validate_json(message)
                except Exception as parse_err:
                    logger.warning(
                        f"Unparsed message from the Live API ({parse_err}): {message}"
                    )
                    continue

                log_server_message(parsed, message)
                if parsed.setup_complete:
                    ready.set()
                if parsed.tool_call:
                    for call in parsed.tool_call.function_calls:
                        spawn(run_function_call(call, state, client_ws, vertex_ws))
                if parsed.tool_call_cancellation:
                    logger.warning(
                        f"Model cancelled tool calls: {parsed.tool_call_cancellation.ids}"
                    )
        except ConnectionClosed as e:
            logger.error(
                f"Live API connection closed. Code: {e.code}, Reason ({len(e.reason.encode('utf-8'))} bytes): {e.reason!r}, "
                f"rcvd={e.rcvd!r}, sent={e.sent!r}"
            )
        except Exception as e:
            logger.error(f"Error in vertex_to_client: {e}", exc_info=True)

    done, pending = await asyncio.wait(
        [
            asyncio.create_task(client_to_vertex()),
            asyncio.create_task(vertex_to_client()),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    for task in background_tasks:
        task.cancel()


def connection_params(websocket: Any) -> dict:
    """Query parameters of the browser's WebSocket URL, e.g. /?avatar=Kira&voice=Aoede"""
    request = getattr(websocket, "request", None)
    path = getattr(request, "path", "") or ""
    return {
        key: values[0]
        for key, values in parse_qs(urlsplit(path).query).items()
        if values
    }


async def handler(websocket: Any):
    logger.info(f"New client connection established from {websocket.remote_address}")
    params = connection_params(websocket)

    logger.info(f"Connecting to Live API at {SERVICE_URL}...")
    try:
        vertex_url = get_vertex_url()
        headers = get_vertex_headers()

        ssl_context = get_ssl_context() if vertex_url.startswith("wss://") else None
        async with websockets.connect(
            vertex_url,
            additional_headers=headers if headers else None,
            ssl=ssl_context,
        ) as vertex_ws:
            logger.info("Connected to the Live API.")

            setup_payload = get_agent_setup_config(
                root_agent, params.get("avatar"), params.get("voice")
            )
            setup = setup_payload["setup"]
            avatar = setup.get("avatar_config", {}).get("avatar_name", "no avatar")
            voice = setup["generation_config"]["speech_config"]["voice_config"][
                "prebuilt_voice_config"
            ]["voice_name"]
            logger.info(
                f"Sending Setup Message with model: {root_agent.model}, avatar {avatar}, voice {voice}..."
            )

            setup_msg = SetupMessage.model_validate(setup_payload)
            await vertex_ws.send(
                setup_msg.model_dump_json(by_alias=True, exclude_none=True)
            )
            logger.info("Session setup message sent.")

            await proxy_bidirectional(websocket, vertex_ws)
    except Exception as e:
        logger.error(f"Failed to connect or maintain session with the Live API: {e}")
        try:
            await websocket.send(json.dumps({"error": str(e)}))
        except Exception:
            pass


def json_response(connection: Any, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    headers = Headers(
        [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-cache"),
        ]
    )
    return Response(HTTPStatus.OK, "OK", headers, body)


def serve_frontend(connection: Any, request: Any):
    """Serves the frontend and /config on the same port; WebSocket upgrades pass through to the handler."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None
    path = request.path.split("?", 1)[0]
    if path == "/config":
        return json_response(
            connection,
            {
                "avatars": AVATARS,
                "voices": VOICES,
                "defaults": {"avatar": default_avatar(), "voice": default_voice()},
                "preset": preset(),
                "proactive": proactive_default(),
                "appName": app_name(),
            },
        )
    if path == "/":
        path = "/index.html"
    file_path = (FRONTEND_DIR / path.lstrip("/")).resolve()
    if not file_path.is_file() or FRONTEND_DIR not in file_path.parents:
        return connection.respond(HTTPStatus.NOT_FOUND, "Not found\n")
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body = file_path.read_bytes()
    # scenes run in a sandboxed iframe with an opaque origin and import three.js from /vendor
    headers = Headers(
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-cache"),
            ("Access-Control-Allow-Origin", "*"),
        ]
    )
    return Response(HTTPStatus.OK, "OK", headers, body)


async def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting VoxPlore backend on {host}:{port}...")
    logger.info(f"Open http://localhost:{port} in your browser.")
    if not (FRONTEND_DIR / "vendor" / "three.module.js").is_file():
        logger.warning(
            "three.js is missing, so interactive scenes will not load. Run: python fetch_three.py"
        )
    async with websockets.serve(
        handler, host, port, process_request=serve_frontend, max_size=48 * 1024 * 1024
    ):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown by user.")
