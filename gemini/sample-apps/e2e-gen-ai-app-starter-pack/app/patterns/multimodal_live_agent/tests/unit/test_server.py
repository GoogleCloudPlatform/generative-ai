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
# pylint: disable=W0707,C0415,W0212

import json
import logging
import os
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from google.auth.credentials import Credentials
import pytest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def mock_google_cloud_credentials() -> Generator[None, None, None]:
    """Mock Google Cloud credentials for testing."""
    with patch.dict(
        os.environ,
        {
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/mock/credentials.json",
            "GOOGLE_CLOUD_PROJECT_ID": "mock-project-id",
        },
    ):
        yield


@pytest.fixture(autouse=True)
def mock_google_auth_default() -> Generator[None, None, None]:
    """Mock the google.auth.default function for testing."""
    mock_credentials = MagicMock(spec=Credentials)
    mock_project = "mock-project-id"

    with patch("google.auth.default", return_value=(mock_credentials, mock_project)):
        yield


@pytest.fixture(autouse=True)
def mock_dependencies() -> Generator[None, None, None]:
    """
    Mock Vertex AI dependencies for testing.
    Patches genai client and tool functions.
    """
    with patch("app.server.genai_client") as mock_genai, patch(
        "app.server.tool_functions"
    ) as mock_tools:
        mock_genai.aio.live.connect = AsyncMock()
        mock_tools.return_value = {}
        yield


@pytest.mark.asyncio
async def test_websocket_endpoint() -> None:
    """
    Test the websocket endpoint to ensure it correctly handles
    websocket connections and messages.
    """
    from app.server import app

    mock_session = AsyncMock()
    mock_session._ws = AsyncMock()
    # Configure mock to return proper response format and close after one message
    mock_session._ws.recv.side_effect = [
        json.dumps(
            {
                "serverContent": {
                    "modelTurn": {
                        "role": "model",
                        "parts": [{"text": "Hello, how can I help you?"}],
                    }
                }
            }
        ).encode(),  # Encode as bytes since recv(decode=False) is used
        None,  # Add None to trigger StopAsyncIteration after first message
    ]

    with patch("app.server.genai_client") as mock_genai:
        mock_genai.aio.live.connect.return_value.__aenter__.return_value = mock_session
        client = TestClient(app)
        with client.websocket_connect("/ws") as websocket:
            # Test initial connection message
            data = websocket.receive_json()
            assert data["status"] == "Backend is ready for conversation"

            # Test sending a message
            websocket.send_json(
                {"setup": {"run_id": "test-run", "user_id": "test-user"}}
            )

            # Test sending audio stream
            dummy_audio = bytes([0] * 1024)  # 1KB of silence
            websocket.send_json(
                {
                    "realtimeInput": {
                        "mediaChunks": [
                            {
                                "mimeType": "audio/pcm;rate=16000",
                                "data": dummy_audio.hex(),
                            }
                        ]
                    }
                }
            )

            # Receive response as bytes
            response = websocket.receive_bytes()
            response_data = json.loads(response.decode())
            assert "serverContent" in response_data

            # Verify mock interactions
            mock_genai.aio.live.connect.assert_called_once()
            assert mock_session._ws.recv.called


@pytest.mark.asyncio
async def test_websocket_error_handling() -> None:
    """Test websocket error handling."""
    from app.server import app

    with patch("app.server.genai_client") as mock_genai:
        mock_genai.aio.live.connect.side_effect = Exception("Connection failed")

        client = TestClient(app)
        with pytest.raises(Exception) as exc:
            with client.websocket_connect("/ws"):
                pass
        assert str(exc.value) == "Connection failed"
