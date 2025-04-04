# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Simple Gemini chat agent for the Concierge demo."""

from concierge import settings, utils
from concierge.langgraph_server import langgraph_agent
from concierge.nodes import chat, save_turn


def load_agent(
    runtime_settings: settings.RuntimeSettings,
) -> langgraph_agent.LangGraphAgent:
    """Loads the simple Gemini chat agent for the Concierge demo."""

    chat_node = chat.build_chat_node(
        node_name="chat",
        next_node="save-turn",
        system_prompt="""
You are an AI assistant for the Cymbal Retail company
Answer questions about the company.
Cymbal offers both online retail and physical stores and carries any safe and appropriate product you can think of.
Feel free to make up information about this fictional company,
this is just for the purposes of a demo.
""".strip(),
    )

    save_turn_node = save_turn.build_save_turn_node(node_name="save-turn")

    gemini_agent = langgraph_agent.LangGraphAgent(
        state_graph=utils.load_graph(
            schema=chat.ChatState,
            nodes=[chat_node, save_turn_node],
            entry_point=chat_node,
        ),
        default_configurable={
            "chat_config": chat.ChatConfig(
                project=runtime_settings.project,
                region=runtime_settings.region,
                chat_model_name=runtime_settings.chat_model_name,
            ),
        },
        checkpointer_config=runtime_settings.checkpointer,
    )

    return gemini_agent
