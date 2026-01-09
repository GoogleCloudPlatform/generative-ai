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


#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.agents import LiveRequestQueue
from google.adk.events import Event
from backend.api.websocket.services import GeminiLiveApiRelaySession


class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.accepted = False
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        # This test only focuses on agent -> client, so client -> agent is not needed
        await asyncio.sleep(100) # Keep task alive indefinitely
        return ""

    async def send_text(self, message: str):
        self.sent_messages.append(message)

    async def close(self, code: int = 1000, reason: str = None):
        self.closed = True

@pytest.mark.asyncio
async def test_receive_from_agent_interrupted_event():
    mock_websocket = MockWebSocket()
    mock_live_request_queue = MagicMock(spec=LiveRequestQueue)
    mock_artifact_service = AsyncMock() # Not directly used in this test, but a dependency
    session_id = "test_session_id"

    relay_session = GeminiLiveApiRelaySession(
        websocket_server=mock_websocket,
        live_request_queue=mock_live_request_queue,
        artifact_service=mock_artifact_service,
        session_id=session_id,
    )

    async def mock_live_events_generator():
        yield Event(interrupted=True, author="agent")

    await relay_session.receive_from_agent(mock_live_events_generator())

    assert len(mock_websocket.sent_messages) == 1
    received_message = json.loads(mock_websocket.sent_messages[0])

    expected_message = {
        "mime_type": "application/json",
        "data": {
            "turn_complete": None, 
            "interrupted": True,
        },
    }
    assert received_message == expected_message

@pytest.mark.asyncio
async def test_receive_from_agent_turn_complete_event():
    mock_websocket = MockWebSocket()
    mock_live_request_queue = MagicMock(spec=LiveRequestQueue)
    mock_artifact_service = AsyncMock()
    session_id = "test_session_id"

    relay_session = GeminiLiveApiRelaySession(
        websocket_server=mock_websocket,
        live_request_queue=mock_live_request_queue,
        artifact_service=mock_artifact_service,
        session_id=session_id,
    )

    async def mock_live_events_generator():
        yield Event(turn_complete=True, author="agent")

    await relay_session.receive_from_agent(mock_live_events_generator())

    assert len(mock_websocket.sent_messages) == 1
    received_message = json.loads(mock_websocket.sent_messages[0])

    expected_message = {
        "mime_type": "application/json",
        "data": {
            "turn_complete": True,
            "interrupted": None,
        },
    }
    assert received_message == expected_message