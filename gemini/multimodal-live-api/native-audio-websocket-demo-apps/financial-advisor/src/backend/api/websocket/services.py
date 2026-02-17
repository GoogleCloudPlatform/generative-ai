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


import re
import asyncio
import base64
import json
import traceback

from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable

from backend.app_logging import get_logger
from backend.app_settings import get_application_settings
from fastapi import WebSocketDisconnect
from google.adk.agents import LiveRequestQueue
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.events import Event
from google.genai import types
from rich.console import Console
from tenacity import retry, stop_after_attempt, wait_exponential
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
)

from .utils import on_backoff, retry_on_connection_error

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = get_logger(__name__)

app_settings = get_application_settings()
console = Console()


class GeminiLiveApiRelaySession:
    def __init__(
        self,
        websocket_server: "WebSocket",
        live_request_queue: LiveRequestQueue,
        artifact_service: InMemoryArtifactService,
        session_id: str,
        notification_text: str | None = None,
    ):
        self.websocket_server: "WebSocket" = websocket_server
        self.live_request_queue = live_request_queue
        self.artifact_service = artifact_service
        self.session_id = session_id
        self.notification_text = notification_text
        self.latest_video_frame: bytes | None = None

    async def send_video_frames(self):
        """Continuously sends the latest video frame to the agent."""
        while True:
            if self.latest_video_frame:
                try:
                    self.live_request_queue.send_realtime(
                        types.Blob(data=self.latest_video_frame, mime_type="image/jpeg")
                    )
                except Exception as e:
                    logger.error(f"Error sending video frame: {e}")
                finally:
                    self.latest_video_frame = None  # Clear after sending
            await asyncio.sleep(0.2)  # 5 FPS

    async def receive_from_client(self):
        while True:
            try:
                message_json = await self.websocket_server.receive_text()
                message = json.loads(message_json)

                mime_type = message.get("mime_type")
                data = message.get("data")
                name = message.get("name")

                if name and data and mime_type == "application/pdf":
                    logger.info(f"[CLIENT TO AGENT] Received file upload: {name} ({mime_type})")
                    decoded_data = base64.b64decode(data)
                    part = types.Part.from_bytes(data=data, mime_type=mime_type)
                    await self.artifact_service.save_artifact(
                        app_name=app_settings.agent.app_name,
                        user_id=app_settings.agent.default_user_id,
                        session_id=self.session_id,
                        filename=name,
                        artifact=part,
                    )
                    logger.info(f"Saved artifact {name} for session {self.session_id}")
                elif mime_type == "text/plain" and data:
                    content = types.Content(role="user", parts=[types.Part.from_text(text=data)])
                    self.live_request_queue.send_content(content=content)
                elif mime_type.startswith("audio/pcm"):
                    if not data:
                        continue
                    decoded_data = base64.b64decode(data)
                    self.live_request_queue.send_realtime(types.Blob(data=decoded_data, mime_type=mime_type))
                elif mime_type == "image/jpeg":
                    if not data:
                        continue
                    self.latest_video_frame = base64.b64decode(data)
                else:
                    logger.warning(f"Mime type not supported or data missing: {mime_type}")
            except WebSocketDisconnect as e:
                logger.error(f"WebSocket disconnected in receive_from_client: {e.code} {e.reason}")
                break
            except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as e:
                logger.error(f"Connection closed in receive_from_client: {e} {e.code} {e.reason}")
                break
            except Exception as e:
                logger.error(f"Caught an exception in receive_from_client: {type(e).__name__} - {e}")
                logger.error(traceback.format_exc())
                break

    async def receive_from_agent(self, live_events: AsyncGenerator[Event, None]):
        try:
            async for event in live_events:
                # If the turn complete or interrupted, send it
                if event.turn_complete or event.interrupted:
                    message = {
                        "mime_type": "application/json",
                        "data": {
                            "turn_complete": event.turn_complete,
                            "interrupted": event.interrupted,
                        },
                    }
                    await self.websocket_server.send_text(json.dumps(message))
                    continue

                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text and not event.partial:
                            source = "user" if event.author == "user" else "agent"
                            response_data = part.text
                            message = {
                                "mime_type": "text/plain",
                                "data": response_data,
                                "source": source,
                            }
                            # Always send the text response
                            await self.websocket_server.send_text(json.dumps(message))
                        elif part.inline_data:  # Correct attribute for audio/media
                            if part.inline_data.data:
                                # The SDK automatically handles the base64 decoding from the API,
                                # so .data gives you raw bytes.
                                # We re-encode to base64 for the WebSocket transmission.
                                encoded_audio = base64.b64encode(part.inline_data.data).decode("utf-8")

                                message = {
                                    "mime_type": part.inline_data.mime_type,  # e.g. "audio/pcm;rate=24000"
                                    "data": encoded_audio,
                                    "source": "agent",
                                }
                                await self.websocket_server.send_text(json.dumps(message))
                                logger.info(f"[AGENT TO CLIENT] Sent audio ({part.inline_data.mime_type}).")

                        ###########################################
                        # Send Loading Animation Visual Indicator #
                        ###########################################
                        if part.function_response and part.function_response.name == "search_financial_documents":
                            logger.info("[AGENT TO CLIENT] RAG AGENT: Sending signal to the frontend...")
                            message = {
                                "mime_type": "application/json",
                                "data": {"visual": {"type": "rag_status", "data": "fetching"}},
                            }
                            await self.websocket_server.send_text(json.dumps(message))

                        if (
                            part.function_call
                            and part.function_call.name == "agent_execution_confirmation_notification"
                        ):
                            logger.info(
                                "[AGENT TO CLIENT] AGENT EXECUTION CONFIRMATION NOTIFICATION TOOL: Sending signal to the frontend..."
                            )

                        ####################################
                        # Generating Appointment Scheduler #
                        ####################################
                        if part.function_response and part.function_response.name == "appointment_scheduler":
                            if isinstance(part.function_response.response, dict):
                                result_str = part.function_response.response.get("result", "{{}}")
                                try:
                                    appointment_scheduler_data = json.loads(result_str)
                                    message = {
                                        "mime_type": "application/json",
                                        "data": appointment_scheduler_data,
                                    }
                                    await self.websocket_server.send_text(json.dumps(message))
                                    logger.info(f"[AGENT TO CLIENT]: appointment_scheduler: {message}")
                                    continue
                                except json.JSONDecodeError:
                                    logger.error(f"Failed to decode appointment_scheduler JSON: {result_str}")

                        #############################################
                        # Agent Execution Confirmation Notification #
                        #############################################
                        if (
                            part.function_response
                            and part.function_response.name == "agent_execution_confirmation_notification"
                        ):
                            if isinstance(part.function_response.response, dict):
                                result_str = part.function_response.response.get("result", "{{}}")
                                try:
                                    agent_execution_confirmation_notification_data = json.loads(result_str)
                                    message = {
                                        "mime_type": "application/json",
                                        "data": agent_execution_confirmation_notification_data,
                                    }
                                    await self.websocket_server.send_text(json.dumps(message))
                                    logger.info(
                                        f"[AGENT TO CLIENT]: agent_execution_confirmation_notification: {message}"
                                    )
                                    continue
                                except json.JSONDecodeError:
                                    logger.error(
                                        f"Failed to decode agent_execution_confirmation_notification JSON: {result_str}"
                                    )

                        ################################
                        # Generating Financial Summary #
                        ################################
                        if (
                            part.function_response
                            and part.function_response.name == "generate_financial_summary_visual"
                        ):
                            if isinstance(part.function_response.response, dict):
                                result_str = part.function_response.response.get("result", "{{}}")
                                try:
                                    generate_financial_summary_visual_data = json.loads(result_str)
                                    message = {
                                        "mime_type": "application/json",
                                        "data": generate_financial_summary_visual_data,
                                    }
                                    await self.websocket_server.send_text(json.dumps(message))
                                    logger.info(f"[AGENT TO CLIENT]: generate_financial_summary_visual: {message}")
                                    continue
                                except json.JSONDecodeError:
                                    logger.error(
                                        f"Failed to decode generate_financial_summary_visual_data JSON: {result_str}"
                                    )

                        ################################
                        # Generating Stock Performance #
                        ################################
                        if part.function_response and part.function_response.name == "stock_performance_agent":
                            if isinstance(part.function_response.response, dict):
                                result_str = part.function_response.response.get("result", "")
                                
                                # Attempt to extract JSON from the result string if it contains extra text
                                extracted_json = result_str
                                try:
                                    # Look for JSON object or array pattern
                                    match = re.search(r'(\{.*\}|\[.*\])', result_str, re.DOTALL)
                                    if match:
                                        potential_json = match.group(0)
                                        # Validate if it is valid JSON
                                        json.loads(potential_json)
                                        extracted_json = potential_json
                                except Exception:
                                    # If parsing fails, fall back to the original string
                                    pass

                                message = {
                                    "mime_type": "application/json",
                                    "data": {
                                        "type": "stock_performance_visual",
                                        "raw_text": extracted_json,
                                    },
                                }
                                await self.websocket_server.send_text(json.dumps(message))
                                logger.info(f"[AGENT TO CLIENT]: stock_performance_visual: {message}")
                                continue

                        ######################################
                        # Generating CD Reinvestment Options #
                        ######################################
                        if part.function_response and part.function_response.name == "display_cd_information":
                            if self.notification_text and "CD maturing" in self.notification_text:
                                if isinstance(part.function_response.response, dict):
                                    result_str = part.function_response.response.get("result", "{{}}")
                                    try:
                                        cd_reinvestment_options_data = json.loads(result_str)
                                        message = {
                                            "mime_type": "application/json",
                                            "data": cd_reinvestment_options_data,
                                        }
                                        await self.websocket_server.send_text(json.dumps(message))
                                        logger.info(f"[AGENT TO CLIENT]: display_cd_information: {message}")
                                        continue
                                    except json.JSONDecodeError:
                                        logger.error(f"Failed to decode display_cd_information JSON: {result_str}")
        except WebSocketDisconnect as e:
            logger.error(f"[red]WebSocket disconnected in receive_from_agent: {e.code} {e.reason}[/red]")
        except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as e:
            logger.error(f"[red]Connection closed in receive_from_agent: {e} \n{e.code} \n{e.reason}[/red]")
        except Exception as e:
            logger.error(f"[red]Error receiving from agent: {type(e).__name__} - {e}[/red]")
            logger.error(traceback.format_exc())


@retry(
    retry=retry_on_connection_error,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before_sleep=on_backoff,
    reraise=True,
)
def get_connect_and_run_callable(
    websocket: "WebSocket",
    live_events: AsyncGenerator[Event, None],
    live_request_queue: LiveRequestQueue,
    notification_text: str | None = None,
    artifact_service: Any = None,
    session_id: str = "",
) -> Callable:
    async def connect_and_run() -> None:
        relay = None
        relay = GeminiLiveApiRelaySession(
            websocket_server=websocket,
            live_request_queue=live_request_queue,
            artifact_service=artifact_service,
            session_id=session_id,
            notification_text=notification_text,
        )

        client_task = asyncio.create_task(relay.receive_from_client())
        agent_task = asyncio.create_task(relay.receive_from_agent(live_events=live_events))
        video_task = asyncio.create_task(relay.send_video_frames())

        # Wait until the websocket is disconnected or an error occurs
        tasks = [client_task, agent_task, video_task]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

        live_request_queue.close()

    return connect_and_run
