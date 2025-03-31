# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import json

from concierge_ui import auth, demo_page, settings
from langgraph.pregel import remote

config = settings.RemoteAgentConfigs().function_calling

graph = remote.RemoteGraph(
    config.name,
    url=str(config.base_url),
    headers=auth.get_auth_headers(config),
)


def chat_handler(message: str, thread_id: str):
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
    for stream_mode, chunk in graph.stream(
        input={
            "current_turn": {
                "user_input": message,
                "user_latitude": 44.6508262,
                "user_longitude": -63.6408055,
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
            print("unhandled chunk case:", chunk)

        if last_source is not None and last_source != current_source:
            text = "\n\n---\n\n" + text

        last_source = current_source

        yield text


demo_page.build_demo_page(
    id="function-calling",
    title="Function Calling Agent",
    page_icon="📞",
    description="""
This demo illustrates an agent grounded on a synthetic BigQuery dataset for a fictional retail company named Cymbal.
Gemini utilizes functions to construct structured SQL queries to retrieve live data during the conversation.
Gemini can additionally use semantic search to rank and filter product search results.
""".strip(),
    chat_handler=chat_handler,
    config=config,
)
