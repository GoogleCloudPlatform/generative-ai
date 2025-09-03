# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import json
import logging

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from vertexai import agent_engines

from src.model.chats import Chat
from src.model.chats import CreateChatRequest
from src.service.chats import ChatsService
from src.service.intent import IntentService
from src.service.intent_matching import IntentMatchingService

DEFAULT_USER_ID = "traveler0115"
INACTIVITY_TIMEOUT_SECONDS = 10 * 60  # 10 minutes

router = APIRouter(
    prefix="/api/chats",
    tags=["chats"],
    responses={404: {"description": "Not found"}},
)


@router.websocket("")
async def websocket_chat(
    *,
    websocket: WebSocket,
    background_tasks: BackgroundTasks,
):
    await websocket.accept()
    active_session_id = "N/A (or setup phase)"

    try:
        # Create a new session for this WebSocket connection
        # This session will be used for the lifetime of this connection.
        intent = get_default_intent()  # General intent for the connection
        remote_agent_resource_id = intent.remote_agent_resource_id
        remote_agent = agent_engines.get(remote_agent_resource_id)
        print(f"WebSocket connected. Agent resource: {remote_agent_resource_id}")
        logging.info(f"WebSocket connected. Agent resource: {remote_agent_resource_id}")

        agent_session = remote_agent.create_session(user_id=DEFAULT_USER_ID)
        active_session_id = agent_session["id"]
        print(f"Created new agent session for WebSocket connection: {active_session_id}")
        logging.info(f"Created new agent session for WebSocket connection: {active_session_id}")

        # Notify client that the session has started, without sending the session ID
        await websocket.send_json({"operation": "start"})

        while True:
            try:
                item_json = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=INACTIVITY_TIMEOUT_SECONDS
                )
                print(f"Received JSON from client: {item_json}")
                logging.info(f"Received JSON from client (session: {active_session_id}): {item_json}")
                # The CreateChatRequest might still have chat_id for HTTP,
                # but we ignore it for WebSocket session management here.
                current_item = CreateChatRequest(**item_json)
            except asyncio.TimeoutError:
                logging.warning(
                    f"Client inactive for {INACTIVITY_TIMEOUT_SECONDS} seconds."
                    f"Closing connection for session: {active_session_id}."
                )
                if websocket.client_state == websocket.client_state.CONNECTED:
                    await websocket.send_json({
                        "operation": "timeout",
                        "message": "Connection closed due to inactivity."
                    })
                break
            except WebSocketDisconnect:
                print(f"Client disconnected (session: {active_session_id}).")
                logging.info("Client disconnected.")
                break  # Exit the main loop
            except json.JSONDecodeError:
                print(f"Failed to decode message as JSON (session: {active_session_id}). Sending error to client.")
                logging.error("Failed to decode message as JSON. Sending error to client.")
                await websocket.send_json({"error": "Invalid JSON format received."})
                continue  # Wait for a new, valid message
            except Exception as e:
                print(f"Error receiving or parsing client message (session: {active_session_id}): {e}")
                logging.error(f"Error receiving or parsing client message: {e}")
                await websocket.send_json(
                    {"error": f"Error processing your request: {str(e)}"}
                )
                break  # Exit on other receive/parse errors

            current_message_text = current_item.text

            print(f"Processing message: '{current_message_text}' for session: {active_session_id}")
            logging.info(f"Processing message: '{current_message_text}' for session: {active_session_id}")
            for event in remote_agent.stream_query(
                user_id=DEFAULT_USER_ID,
                session_id=active_session_id,  # Use the session created for this connection
                message=current_message_text,
            ):
                content = event.get("content")
                if content:
                    for part in event["content"]["parts"]:
                        # Send only the answer part, no session ID needed by client here
                        answer_part = {"answer": part}
                        await websocket.send_json(answer_part)
                        log_response(
                            background_tasks,
                            intent,
                            current_message_text,
                            json.dumps(part),  # Log the streamed part
                            agent_session,  # Pass the created agent_session object
                            [],  # Suggested questions for this part
                        )

            # After streaming all parts for the current message's response
            # Signal end of turn, no session ID needed by client here
            await websocket.send_json({"operation": "end_of_turn"})
            print(f"Sent 'end_of_turn' for session: {active_session_id}. Waiting for next client message...")
            logging.info(f"Sent 'end_of_turn' for session: {active_session_id}. Waiting for next client message...")

    except WebSocketDisconnect:
        print(f"WebSocket disconnected during operation (session: {active_session_id}).")
        logging.error(f"WebSocket disconnected during operation (session: {active_session_id}).")
    except Exception as e:
        print(f"An unhandled error occurred in WebSocket handler (session: {active_session_id}): {e}")
        logging.error(f"An unhandled error occurred in WebSocket handler (session: {active_session_id}): {e}")
        try:
            if websocket.client_state == websocket.client_state.CONNECTED:
                await websocket.send_json(
                    {
                        "error": f"An unexpected server error occurred in WebSocket handler (session: {active_session_id}): {e}",
                        "operation": "fatal_error",
                    }
                )
        except Exception as send_exc:
            print(f"Could not send error to client: {send_exc}")
    finally:
        print(f"Closing WebSocket connection from server-side finally block (session: {active_session_id}).")
        logging.info(f"Closing WebSocket connection from server-side finally block (session: {active_session_id}).")
        if websocket.client_state == websocket.client_state.CONNECTED:
            await websocket.close()


# The log_response and get_default_intent functions are still used by the websocket_chat endpoint.
def log_response(
    background_tasks,
    intent,
    message,
    model_response_content,
    session_details,
    suggested_questions,
):
    final_response = Chat(
        id=session_details["id"],  # The session_details will have the id
        question=message,
        answer=model_response_content,
        intent=intent.name,
        suggested_questions=suggested_questions,
    )
    background_tasks.add_task(
        ChatsService().insert_chat,
        final_response,
    )
    return final_response


def get_default_intent():
    intents = IntentService().get_all()
    intent_matching_service = IntentMatchingService(intents)
    intent = intent_matching_service.get_intent_from_query("")
    return intent
