# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""LangGraph agent for a chat assistant with guardrail classification."""

# disable duplicate code to make it easier for copying a single agent folder
# pylint: disable=duplicate-code

from concierge.agents.gemini_chat_with_guardrails import schemas
from concierge.agents.gemini_chat_with_guardrails.nodes import (
    chat,
    guardrails,
    post_process,
)
from langchain_core.runnables import config
from langgraph.graph import StateGraph

FINAL_NODE = schemas.POST_PROCESS_NODE_NAME


def load_graph() -> StateGraph:
    """
    Creates and configures a LangGraph representing a chat assistant with guardrail classification.

    This function defines the structure of the agent's interaction flow using a StateGraph.
    It adds nodes for guardrail classification, chat interaction, and post-processing. The
    guardrail node is set as the entry point, ensuring that all user inputs are first
    evaluated for safety before proceeding to the chat node.

    Returns:
        StateGraph: A LangGraph object representing the agent's conversation flow with guardrails.
    """

    # Graph
    graph = StateGraph(
        state_schema=schemas.GraphSession,
        config_schema=config.RunnableConfig,
    )

    # Nodes
    graph.add_node(schemas.GUARDRAILS_NODE_NAME, guardrails.ainvoke)
    graph.add_node(schemas.CHAT_NODE_NAME, chat.ainvoke)
    graph.add_node(schemas.POST_PROCESS_NODE_NAME, post_process.ainvoke)
    graph.set_entry_point(schemas.GUARDRAILS_NODE_NAME)

    return graph
