# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# disable duplicate code since chat handlers for each agent may be very similar
# pylint: disable=duplicate-code

import json
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
    Handles chat interactions for a function calling agent by streaming responses from a remote LangGraph.

    This function takes a user message and a thread ID, and streams responses from a remote LangGraph.
    It parses the streamed chunks, which can contain text responses, function calls, function responses, or errors,
    and formats them into a human-readable text stream.

    Args:
        message (str): The user's input message.
        thread_id (str): The ID of the chat thread.

    Yields:
        str: Formatted text chunks representing text responses, function calls, function responses, or errors.
    """
    current_source = last_source = None
    for _, chunk in graph.stream(
        input={
            "current_turn": {
                "user_input": message,
                "user_location": {"latitude": 44.6508262, "longitude": -63.6408055},
            }
        },
        config={"configurable": {"thread_id": thread_id}},
        stream_mode=["custom"],
    ):
        assert isinstance(chunk, dict), "Expected dictionary chunk"

        text = ""

        if "text" in chunk:
            text = chunk["text"]
            current_source = "text"

        elif "function_call" in chunk:
            function_call_dict = chunk["function_call"]

            fn_name = function_call_dict.get("name") or "unknown"
            fn_args = function_call_dict.get("args") or {}

            fn_args_string = ", ".join(f"{k}={v}" for k, v in fn_args.items())
            fn_string = f"**{fn_name}**({fn_args_string})"

            text = f"Calling function... {fn_string}"
            current_source = "function_call"

        elif "function_response" in chunk:
            function_response_dict = chunk["function_response"]

            fn_name = function_response_dict.get("name") or "unknown"

            if function_response_dict.get("response") is None:
                text = f"Received empty function response (name={fn_name})."

            elif "result" in function_response_dict.get("response"):
                fn_result = function_response_dict["response"]["result"]
                text = "\n\n".join(
                    [
                        f"Function result for **{fn_name}**...",
                        "```json",
                        json.dumps(fn_result, indent=2),
                        "```",
                    ]
                )

            elif "error" in function_response_dict.get("response"):
                fn_result = function_response_dict["response"]["error"]
                text = f"Function error (name={fn_name})... {fn_result}"

            current_source = "function_response"

        elif "error" in chunk:
            text = chunk["error"]
            current_source = "error"

        else:
            logger.warning(f"unhandled chunk case: {chunk}")

        if last_source is not None and last_source != current_source:
            text = "\n\n---\n\n" + text

        last_source = current_source

        yield text
