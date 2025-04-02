# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""LangGraph agent for a chat assistant."""

# disable duplicate code to make it easier for copying a single agent folder
# pylint: disable=duplicate-code

from concierge.agents.gemini_chat import schemas
from concierge.agents.gemini_chat.nodes import chat, post_process
from langchain_core.runnables import config
from langgraph.graph import StateGraph

FINAL_NODE = schemas.POST_PROCESS_NODE_NAME


def load_graph() -> StateGraph:
    """
    Creates and configures a LangGraph representing the conversational agent's workflow.

    This function defines the structure of the agent's interaction flow using a StateGraph.
    It adds nodes for chat interaction and post-processing, and sets the entry point for
    the graph.

    Returns:
        StateGraph: A LangGraph object representing the agent's conversation flow.
    """

    # Graph
    graph = StateGraph(
        state_schema=schemas.GraphSession,
        config_schema=config.RunnableConfig,
    )

    # Nodes
    graph.add_node(schemas.CHAT_NODE_NAME, chat.ainvoke)
    graph.add_node(schemas.POST_PROCESS_NODE_NAME, post_process.ainvoke)
    graph.set_entry_point(schemas.CHAT_NODE_NAME)

    return graph
