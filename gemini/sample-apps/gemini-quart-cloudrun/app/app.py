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
# pylint: disable=too-many-lines
# pylint: disable=import-error

import asyncio
import json
import logging
import os
from typing import Any, Dict

from google.genai import Client
from google.genai.live import AsyncSession
from google.genai.types import LiveConnectConfig
from quart import Quart, Response, Websocket, send_from_directory, websocket

logging.basicConfig(level=logging.INFO)

#
# Gemini API
#

PROJECT_ID: str = os.environ.get("PROJECT_ID", "")
LOCATION: str = os.environ.get("LOCATION", "us-central1")
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
QUART_DEBUG_MODE: bool = os.environ.get("QUART_DEBUG_MODE") == "True"

GEMINI_MODEL: str = "gemini-2.0-flash-live-preview-04-09"

# Gemini API Client: Use either one of the following APIs
gemini_client: Client = (
    Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    if not GEMINI_API_KEY
    else Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1alpha"})
)

# Gemini API config
gemini_config = LiveConnectConfig(
    response_modalities=["TEXT"],
)

#
# Quart
#

app: Quart = Quart(__name__)


@app.route("/")
async def index() -> Response:
    """
    Serve index.html for the index access.
    """
    return await send_from_directory("public", "index.html")


async def upstream_worker(
    gemini_session: AsyncSession, client_websocket: Websocket
) -> None:
    """
    Continuously read messages from the client WebSocket
    and forward them to Gemini.
    """
    while True:
        message: str = await client_websocket.receive()
        await gemini_session.send(input=message, end_of_turn=True)
        logging.info(
            "upstream_worker(): sent a message from client to Gemini: %s", message
        )


async def downstream_worker(
    gemini_session: AsyncSession, client_websocket: Websocket
) -> None:
    """
    Continuously read streaming responses from Gemini
    and send them directly to the client WebSocket.
    """
    while True:
        async for response in gemini_session.receive():
            if not response:
                continue

            packet: Dict[str, Any] = {
                "text": response.text if response.text else "",
                "turn_complete": response.server_content.turn_complete,
            }
            await client_websocket.send(json.dumps(packet))
            logging.info("downstream_worker(): sent response to client: %s", packet)


@app.websocket("/live")
async def live() -> None:
    """
    WebSocket endpoint for live (streaming) connections to Gemini.
    """

    # Connect to Gemini in "live" (streaming) mode
    async with gemini_client.aio.live.connect(
        model=GEMINI_MODEL, config=gemini_config
    ) as gemini_session:
        upstream_task: asyncio.Task = asyncio.create_task(
            upstream_worker(gemini_session, websocket)
        )
        downstream_task: asyncio.Task = asyncio.create_task(
            downstream_worker(gemini_session, websocket)
        )
        logging.info("live(): connected to Gemini, started workers.")

        try:
            # Wait until either task finishes or raises an exception
            done, pending = await asyncio.wait(
                [downstream_task, upstream_task], return_when=asyncio.FIRST_EXCEPTION
            )

            # If one of them raised, re-raise that exception here
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc:
                    raise exc

        # Handle cancelled errors
        except asyncio.CancelledError:
            logging.info("live(): client connection closed.")

        finally:
            # Cancel any leftover tasks
            upstream_task.cancel()
            downstream_task.cancel()
            await asyncio.gather(downstream_task, upstream_task, return_exceptions=True)

            # Close Gemini session
            await gemini_session.close()
            logging.info("live(): Gemini session closed.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=QUART_DEBUG_MODE)
