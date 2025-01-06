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
# pylint: disable=R0801,C0415
from unittest.mock import patch

from app.utils.output_types import OnToolEndEvent
from langchain_core.documents import Document
from langchain_core.messages import AIMessageChunk, HumanMessage
import pytest

CHAIN_NAME = "Agentic RAG Vertex AI Search agent"


@pytest.mark.asyncio
async def test_agentic_rag_vertex_ai_search_astream_events() -> None:
    """
    Integration testing example for the Agentic RAG Vertex AI Search agent chain. We assert that the chain returns
    events, containing AIMessageChunks and tool usage events for document retrieval.
    """

    # We mock the Vector DBs call to avoid to create this dependency during integration tests
    # Patch the retrieve_docs function to return our mock document
    with patch("app.chain.retrieve_docs.func") as mock_retrieve:
        from app.chain import chain

        # Mock document to be returned by retrieve_docs
        mock_doc = Document(
            page_content="Test document content", metadata={"source": "test_source"}
        )
        mock_retrieve.return_value = ("dummy content", [mock_doc])

        user_message = HumanMessage("What is MLOps?")
        input_dict = {"messages": [user_message]}

        events = [
            event async for event in chain.astream_events(input_dict, version="v2")
        ]

        assert len(events) > 1, (
            f"Expected multiple events for {CHAIN_NAME} chain, " f"got {len(events)}"
        )
        on_tool_end_events = [
            event for event in events if event["event"] == "on_tool_end"
        ]

        assert len(on_tool_end_events) == 1, (
            f"Expected exactly one on_tool_end event for {CHAIN_NAME} chain, "
            f"got {len(on_tool_end_events)}"
        )
        assert isinstance(
            OnToolEndEvent.model_validate(on_tool_end_events[0]), OnToolEndEvent
        )

        on_chain_stream_events = [
            event for event in events if event["event"] == "on_chat_model_stream"
        ]

        assert on_chain_stream_events, (
            f"Expected at least one on_chat_model_stream event"
            f" for {CHAIN_NAME} chain"
        )

        for event in on_chain_stream_events:
            assert AIMessageChunk.model_validate(
                event["data"]["chunk"]
            ), f"Invalid AIMessageChunk for {CHAIN_NAME} chain: {event['data']['chunk']}"
