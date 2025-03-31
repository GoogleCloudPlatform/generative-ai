# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

from langgraph.pregel import remote

from concierge_ui import settings, demo_page, auth

config = settings.RemoteAgentConfigs().semantic_router

graph = remote.RemoteGraph(
    config.name,
    url=str(config.base_url),
    headers=auth.get_auth_headers(config),
)


def chat_handler(message: str, thread_id: str):
    """
    Handles chat interactions for a semantic router agent by streaming responses from a remote LangGraph.

    This function takes a user message and a thread ID, and streams responses from a remote LangGraph.
    It parses the streamed chunks, which can contain router classifications, text responses, or errors,
    and formats them into a human-readable text stream.

    Args:
        message (str): The user's input message.
        thread_id (str): The ID of the chat thread.

    Yields:
        str: Formatted text chunks representing router classifications, text responses, or errors.
    """
    current_source = last_source = None
    for stream_mode, chunk in graph.stream(
        input={"current_turn": {"user_input": message}},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode=["custom"],
    ):
        assert isinstance(chunk, dict), "Expected dictionary chunk"

        text = ""

        if "router_classification" in chunk:
            target = chunk["router_classification"]["target"]
            reason = chunk["router_classification"]["reason"]

            text = f"Agent Classification: {target}\n\nReason: {reason}"
            current_source = "router_classification"

        elif "text" in chunk:
            text = chunk["text"]
            current_source = "text"

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
    id="semantic-router",
    title="Semantic Router",
    page_icon="↗️",
    description="""
This demo illustrates a semantic router agent. The router acts as a classifier that routes to sub-agent "experts".
The router in this example can either reject the query, route to a retail assistant, or customer service agent.
For the purposes of this demo the experts are just calls to a Gemini model with a simple system prompt.

This pattern can be particularly useful if you have multiple assistants (e.g. LangGraph, CCAI, Agent Builder)
but want to offer a unified chat interface with shared session history across each assistant.
""".strip(),
    chat_handler=chat_handler,
    config=config,
)
