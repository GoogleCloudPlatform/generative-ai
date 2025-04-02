# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""LangGraph agent for a function calling assistant."""

# disable duplicate code to make it easier for copying a single agent folder
# pylint: disable=duplicate-code

from concierge.agents.function_calling import schemas
from concierge.agents.function_calling.nodes import chat, post_process
from langchain_core.runnables import config
from langgraph.graph import StateGraph

FINAL_NODE = schemas.POST_PROCESS_NODE_NAME


def load_graph() -> StateGraph:
    """
    Loads and configures the LangGraph state graph for the function calling agent.

    This function defines the nodes of the graph, which include a chat node (for
    handling conversation and function calls) and a post-processing node. It also
    sets the entry point of the graph to the chat node.

    Returns:
        StateGraph: The configured LangGraph state graph.
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
