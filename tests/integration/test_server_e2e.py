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
# pylint: disable=W0621, W0613, R0801, R1732

import json
import logging
import subprocess
import sys
import threading
import time
from typing import Any, Iterator
import uuid

import pytest
import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000/"
STREAM_EVENTS_URL = BASE_URL + "stream_events"
FEEDBACK_URL = BASE_URL + "feedback"

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
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
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
        except RequestException:
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


def test_chat_stream(server_fixture: subprocess.Popen[str]) -> None:
    """Test the chat stream functionality."""
    logger.info("Starting chat stream test")

    data = {
        "input": {
            "messages": [
                {"type": "human", "content": "Hello, AI!"},
                {"type": "ai", "content": "Hello!"},
                {"type": "human", "content": "What cooking recipes do you suggest?"},
            ],
            "user_id": "test-user",
            "session_id": "test-session",
        }
    }

    response = requests.post(
        STREAM_EVENTS_URL, headers=HEADERS, json=data, stream=True, timeout=10
    )
    assert response.status_code == 200

    events = [json.loads(line) for line in response.iter_lines() if line]
    logger.info(f"Received {len(events)} events")

    assert len(events) > 2, f"Expected more than 2 events, got {len(events)}."
    assert events[0]["event"] == "metadata", (
        f"First event should be 'metadata', " f"got {events[0]['event']}"
    )
    assert "run_id" in events[0]["data"], "Missing 'run_id' in metadata"

    event_types = [event["event"] for event in events]
    assert "on_chat_model_stream" in event_types, "Missing 'on_chat_model_stream' event"
    assert events[-1]["event"] == "end", (
        f"Last event should be 'end', " f"got {events[-1]['event']}"
    )

    logger.info("Test completed successfully")


def test_chat_stream_error_handling(server_fixture: subprocess.Popen[str]) -> None:
    """Test the chat stream error handling."""
    logger.info("Starting chat stream error handling test")

    data = {"input": [{"type": "invalid_type", "content": "Cause an error"}]}
    response = requests.post(
        STREAM_EVENTS_URL, headers=HEADERS, json=data, stream=True, timeout=10
    )

    assert response.status_code == 422, (
        f"Expected status code 422, " f"got {response.status_code}"
    )
    logger.info("Error handling test completed successfully")


def test_collect_feedback(server_fixture: subprocess.Popen[str]) -> None:
    """
    Test the feedback collection endpoint (/feedback) to ensure it properly
    logs the received feedback.
    """
    # Create sample feedback data
    feedback_data = {
        "score": 4,
        "run_id": str(uuid.uuid4()),
        "text": "Great response!",
    }

    response = requests.post(
        FEEDBACK_URL, json=feedback_data, headers=HEADERS, timeout=10
    )
    assert response.status_code == 200
