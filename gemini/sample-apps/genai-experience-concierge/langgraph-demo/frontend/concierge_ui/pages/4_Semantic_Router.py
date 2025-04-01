# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

from concierge_ui import auth, demo_page
from concierge_ui import remote_settings as settings
from langgraph.pregel import remote

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
    for _, chunk in graph.stream(
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
This demo uses an LLM-based intent detection classifier to route each user query to either a "Retail Search" or "Customer Support" expert assistant. The experts are mocked as simple Gemini calls with a system prompt for this demo, but represent an arbitrary actor that can share session history with all other sub-agents. For example, the customer support agent might be implemented with [Contact Center as a Service](https://cloud.google.com/solutions/contact-center-ai-platform) while the retail search assistant is built with Gemini and deployed on Cloud Run.

The semantic router layer can provide a useful facade to enable a single interface for multiple drastically different agent backends.
""".strip(),
    chat_handler=chat_handler,
    config=config,
)
