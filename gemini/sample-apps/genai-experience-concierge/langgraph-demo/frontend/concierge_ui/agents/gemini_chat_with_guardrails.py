# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# disable duplicate code since chat handlers for each agent may be very similar
# pylint: disable=duplicate-code

import logging
from typing import Generator

from langgraph.pregel import remote

logger = logging.getLogger(__name__)


def chat_handler(
    graph: remote.RemoteGraph,
    message: str,
    thread_id: str,
) -> Generator[str, None, None]:
    """
    Handles chat interactions for a guardrail agent by streaming responses from a remote LangGraph.

    This function takes a user message and a thread ID, and streams responses from a remote LangGraph.
    It parses the streamed chunks, which can contain guardrail classifications, text responses, or errors,
    and formats them into a human-readable text stream.

    Args:
        message (str): The user's input message.
        thread_id (str): The ID of the chat thread.

    Yields:
        str: Formatted text chunks representing guardrail classifications, text responses, or errors.
    """
    current_source = last_source = None
    for _, chunk in graph.stream(
        input={"current_turn": {"user_input": message}},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode=["custom"],
    ):
        assert isinstance(chunk, dict), "Expected dictionary chunk"

        text = ""

        if "guardrail_classification" in chunk:
            is_blocked = chunk["guardrail_classification"]["blocked"]
            classification_emoji = "❌" if is_blocked else "✅"
            reason = chunk["guardrail_classification"]["reason"]

            text = (
                f"Guardrail classification: {classification_emoji}\n\nReason: {reason}"
            )
            current_source = "guardrail_classification"

        elif "text" in chunk:
            text = chunk["text"]
            current_source = "text"

        elif "error" in chunk:
            text = chunk["error"]
            current_source = "error"

        else:
            logger.warning(f"unhandled chunk case: {chunk}")

        if last_source is not None and last_source != current_source:
            text = "\n\n---\n\n" + text

        last_source = current_source

        yield text
