# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

from concierge_ui import auth, demo_page
from concierge_ui import remote_settings as settings
from langgraph.pregel import remote

config = settings.RemoteAgentConfigs().guardrail

graph = remote.RemoteGraph(
    config.name,
    url=str(config.base_url),
    headers=auth.get_auth_headers(config),
)


def chat_handler(message: str, thread_id: str):
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
            print("unhandled chunk case:", chunk)

        if last_source is not None and last_source != current_source:
            text = "\n\n---\n\n" + text

        last_source = current_source

        yield text


demo_page.build_demo_page(
    id="gemini-chat-with-guardrails",
    title="Gemini Chat With Guardrails",
    page_icon="🛡️",
    description="""
This demo illustrates a Gemini-based chatbot protected with a custom guardrail classifier.

Before generating a chat response, the user input and conversation history is passed to
a smaller, faster Gemini model which classifies the response as allowed or blocked.

* If the input is blocked, a fallback response is returned to the user.
* Otherwise, a larger Gemini model is used to generate and stream a response.
""".strip(),
    chat_handler=chat_handler,
    config=config,
)
