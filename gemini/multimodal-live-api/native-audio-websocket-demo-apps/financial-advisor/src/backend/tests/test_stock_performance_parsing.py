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
import re
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.agents import LiveRequestQueue
from google.adk.events import Event
from google.genai import types # Corrected import
from backend.api.websocket.services import GeminiLiveApiRelaySession


class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.accepted = False
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        await asyncio.sleep(100)  # Keep task alive indefinitely
        return ""

    async def send_text(self, message: str):
        self.sent_messages.append(message)

    async def close(self, code: int = 1000, reason: str = None):
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw_agent_response",
    [
        # Case 1: Text before JSON
        "Here is the stock data: {\"stockName\": \"GOOGL\", \"price\": \"$100\"}",
        # Case 2: Markdown code block around JSON
        "```json\n{\"stockName\": \"NVDA\", \"price\": \"$200\"}\n```",
        # Case 3: Pure JSON (should pass through)
        "{\"stockName\": \"MSFT\", \"price\": \"$300\"}",
        # Case 4: Text after JSON
        "{\"stockName\": \"AMZN\", \"price\": \"$400\"} And that's all.",
        # Case 5: Complex text with JSON in middle
        "The analysis shows: {\"stockName\": \"TSLA\", \"price\": \"$500\"} which is great news!",
        # Case 6: JSON array
        "Here are some stocks: [{\"stockName\": \"AAPL\", \"price\": \"$600\"}, {\"stockName\": \"NFLX\", \"price\": \"$700\"}]"
    ],
)
async def test_receive_from_agent_stock_performance_json_parsing(raw_agent_response: str):
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

    # The expected pure JSON part to be extracted
    match = re.search(r'(\{.*\}|\[.*\])', raw_agent_response, re.DOTALL)
    expected_extracted_json_str = match.group(0) if match else raw_agent_response

    async def mock_live_events_generator():
        function_response = types.FunctionResponse(
            name="stock_performance_agent",
            response={'result': raw_agent_response},
        )
        function_response_part = types.Part(function_response=function_response)
        
        yield Event(
            content=types.Content(parts=[function_response_part]), # Corrected instantiation
            author="agent",  # Required by ADK Event
        )

    await relay_session.receive_from_agent(mock_live_events_generator())

    assert len(mock_websocket.sent_messages) == 1
    received_message = json.loads(mock_websocket.sent_messages[0])

    assert received_message["mime_type"] == "application/json"
    assert received_message["data"]["type"] == "stock_performance_visual"
    
    # Assert that the raw_text is now clean JSON that can be parsed
    assert json.loads(received_message["data"]["raw_text"]) == json.loads(expected_extracted_json_str)

    # Ensure the original raw_text (potentially with extra content) is not directly passed if it was malformed
    if match: # If there was something to extract, ensure it's not the original malformed string
        assert received_message["data"]["raw_text"] != raw_agent_response or \
               received_message["data"]["raw_text"] == expected_extracted_json_str
    else:
        # If no JSON was found, it should still be the original string (though this test focuses on success)
        assert received_message["data"]["raw_text"] == raw_agent_response