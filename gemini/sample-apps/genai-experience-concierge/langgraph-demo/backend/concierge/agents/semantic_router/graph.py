# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""LangGraph graph for an agent with a semantic router."""

# disable duplicate code to make it easier for copying a single agent folder
# pylint: disable=duplicate-code

from concierge.agents.semantic_router import schemas
from concierge.agents.semantic_router.nodes import (
    customer_service_assistant,
    post_process,
    retail_assistant,
    router,
)
from langchain_core.runnables import config
from langgraph.graph import StateGraph

FINAL_NODE = schemas.POST_PROCESS_NODE_NAME


def load_graph() -> StateGraph:
    """
    Creates and configures a LangGraph representing an agent with a semantic router.

    This function defines the structure of the agent's interaction flow using a StateGraph.
    It adds nodes for routing, retail assistance, customer service assistance, and post-processing.
    The router node is set as the entry point, ensuring that all user inputs are first
    routed to the appropriate sub-agent based on their semantic meaning.

    Returns:
        StateGraph: A LangGraph object representing the agent's conversation flow with routing.
    """

    # Graph
    graph = StateGraph(
        state_schema=schemas.GraphSession,
        config_schema=config.RunnableConfig,
    )

    # Nodes
    graph.add_node(schemas.ROUTER_NODE_NAME, router.ainvoke)
    graph.add_node(schemas.RETAIL_NODE_NAME, retail_assistant.ainvoke)
    graph.add_node(
        schemas.CUSTOMER_SERVICE_NODE_NAME, customer_service_assistant.ainvoke
    )
    graph.add_node(schemas.POST_PROCESS_NODE_NAME, post_process.ainvoke)
    graph.set_entry_point(schemas.ROUTER_NODE_NAME)

    return graph
