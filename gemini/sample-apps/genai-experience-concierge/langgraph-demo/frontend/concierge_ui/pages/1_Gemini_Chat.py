# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

from concierge_ui import auth, demo_page, remote_settings as settings
from langgraph.pregel import remote

config = settings.RemoteAgentConfigs().gemini

graph = remote.RemoteGraph(
    config.name,
    url=str(config.base_url),
    headers=auth.get_auth_headers(config),
)


def chat_handler(message: str, thread_id: str):
    """
    Handles chat interactions for a basic Gemini chat agent by streaming responses from a remote LangGraph.

    This function takes a user message and a thread ID, and streams responses from a remote LangGraph.
    It parses the streamed chunks, which can contain text responses or errors,
    and formats them into a human-readable text stream.

    Args:
        message (str): The user's input message.
        thread_id (str): The ID of the chat thread.

    Yields:
        str: Formatted text chunks representing text responses or errors.
    """
    current_source = last_source = None
    for stream_mode, chunk in graph.stream(
        input={"current_turn": {"user_input": message}},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode=["custom"],
    ):
        assert isinstance(chunk, dict), "Expected dictionary chunk"

        text = ""

        if "text" in chunk:
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
    id="gemini-chat",
    title="Gemini Chat",
    page_icon="⭐",
    description="""
This demo illustrates a simple "agent" which just consists of plain Gemini 2.0 Flash with conversation history.
Response text is streamed using a custom [langgraph.config.get_stream_writer](https://langchain-ai.github.io/langgraph/reference/config/#langgraph.config.get_stream_writer).
""".strip(),
    chat_handler=chat_handler,
    config=config,
)
