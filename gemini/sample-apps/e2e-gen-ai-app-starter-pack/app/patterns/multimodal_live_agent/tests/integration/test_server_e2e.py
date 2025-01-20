# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=W0621, W0613, R0801, R1732, W0718, E1101, R0912

import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, Iterator
import uuid

import pytest
import requests
import websockets.client

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_URL = "ws://127.0.0.1:8000/"
WS_URL = BASE_URL + "ws"

FEEDBACK_URL = "http://127.0.0.1:8000/feedback"
HEADERS = {"Content-Type": "application/json"}


def log_output(pipe: Any, log_func: Any) -> None:
    """Log the output from the given pipe."""
    for line in iter(pipe.readline, ""):
        log_func(line.strip())


def start_server() -> subprocess.Popen[str]:
    """Start the FastAPI server using subprocess and log its output."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.server:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    env = os.environ.copy()
    env["INTEGRATION_TEST"] = "TRUE"
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    # Start threads to log stdout and stderr in real-time
    threading.Thread(
        target=log_output, args=(process.stdout, logger.info), daemon=True
    ).start()
    threading.Thread(
        target=log_output, args=(process.stderr, logger.error), daemon=True
    ).start()

    return process


def wait_for_server(timeout: int = 60, interval: int = 1) -> bool:
    """Wait for the server to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get("http://127.0.0.1:8000/docs", timeout=10)
            if response.status_code == 200:
                logger.info("Server is ready")
                return True
        except Exception:
            pass
        time.sleep(interval)
    logger.error(f"Server did not become ready within {timeout} seconds")
    return False


@pytest.fixture(scope="session")
def server_fixture(request: Any) -> Iterator[subprocess.Popen[str]]:
    """Pytest fixture to start and stop the server for testing."""
    logger.info("Starting server process")
    server_process = start_server()
    if not wait_for_server():
        pytest.fail("Server failed to start")
    logger.info("Server process started")

    def stop_server() -> None:
        logger.info("Stopping server process")
        server_process.terminate()
        server_process.wait()
        logger.info("Server process stopped")

    request.addfinalizer(stop_server)
    yield server_process


@pytest.mark.asyncio
async def test_websocket_connection(server_fixture: subprocess.Popen[str]) -> None:
    """Test the websocket connection and message exchange."""

    async def send_message(websocket: Any, message: Dict[str, Any]) -> None:
        """Helper function to send messages and log them."""
        await websocket.send(json.dumps(message))

    async def receive_message(websocket: Any, timeout: float = 5.0) -> Dict[str, Any]:
        """Helper function to receive messages with timeout."""
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            if isinstance(response, bytes):
                return json.loads(response.decode())
            if isinstance(response, str):
                return json.loads(response)
            return response
        except asyncio.TimeoutError as exc:
            raise TimeoutError(
                f"No response received within {timeout} seconds"
            ) from exc

    try:
        await asyncio.sleep(2)

        async with websockets.connect(
            WS_URL, ping_timeout=10, close_timeout=10
        ) as websocket:
            try:
                # Wait for initial ready message
                initial_response = None
                for _ in range(10):
                    try:
                        initial_response = await receive_message(websocket, timeout=5.0)
                        if (
                            initial_response is not None
                            and initial_response.get("status")
                            == "Backend is ready for conversation"
                        ):
                            break
                    except TimeoutError:
                        if _ == 9:
                            raise
                        continue

                assert (
                    initial_response is not None
                    and initial_response.get("status")
                    == "Backend is ready for conversation"
                )

                # Send messages
                setup_msg = {"setup": {"run_id": "test-run", "user_id": "test-user"}}
                await send_message(websocket, setup_msg)

                dummy_audio = bytes([0] * 1024)
                audio_msg = {
                    "realtimeInput": {
                        "mediaChunks": [
                            {
                                "mimeType": "audio/pcm;rate=16000",
                                "data": dummy_audio.hex(),
                            }
                        ]
                    }
                }
                await send_message(websocket, audio_msg)

                text_msg = {
                    "clientContent": {
                        "turns": [
                            {"role": "user", "parts": [{"text": "Hello, how are you?"}]}
                        ],
                        "turnComplete": True,
                    }
                }
                await send_message(websocket, text_msg)

                # Collect responses with timeout
                responses = []
                try:
                    while True:
                        try:
                            response = await receive_message(websocket, timeout=10.0)
                            responses.append(response)
                            if (
                                len(responses) >= 3
                            ):  # Exit after receiving enough responses
                                break
                        except TimeoutError:
                            break
                except asyncio.TimeoutError:
                    logger.info("Response collection timed out")

                # Verify responses
                assert len(responses) > 0, "No responses received from server"
                assert any(
                    isinstance(r, dict) and "serverContent" in r for r in responses
                )
                logger.info(
                    f"Test completed successfully. Received {len(responses)} responses"
                )

            finally:
                # Ensure websocket is closed properly
                await websocket.close()

    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise

    finally:
        # Clean up any remaining tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def test_collect_feedback(server_fixture: subprocess.Popen[str]) -> None:
    """
    Test the feedback collection endpoint (/feedback) to ensure it properly
    logs the received feedback.
    """
    # Create sample feedback data
    feedback_data = {
        "score": 4,
        "text": "Great response!",
        "run_id": str(uuid.uuid4()),
        "user_id": "user1",
        "log_type": "feedback",
    }

    response = requests.post(
        FEEDBACK_URL, json=feedback_data, headers=HEADERS, timeout=10
    )
    assert response.status_code == 200
