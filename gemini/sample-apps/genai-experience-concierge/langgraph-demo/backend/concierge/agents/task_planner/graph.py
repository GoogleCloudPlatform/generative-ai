# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""LangGraph agent for a task planner assistant."""

from concierge.agents.task_planner import schemas
from concierge.agents.task_planner.nodes import (
    executor,
    planner,
    post_process,
    reflector,
)
from langchain_core.runnables import config
from langgraph.graph import StateGraph

FINAL_NODE = schemas.POST_PROCESS_NODE_NAME


def load_graph():
    """
    Creates and configures a LangGraph representing a task planner agent.

    This function defines the structure of the agent's workflow using a StateGraph.
    It adds nodes for planning, executing tasks, reflecting on the results, and post-processing.
    The planner node is set as the entry point, initiating the process of generating a research plan
    based on user input. The graph then orchestrates the execution of these plan steps,
    reflection on the outcomes, and ultimately generates a response or initiates a new plan.

    Returns:
        StateGraph: A LangGraph object representing the agent's task planning and execution flow.
    """

    # Graph
    graph = StateGraph(
        state_schema=schemas.GraphSession,
        config_schema=config.RunnableConfig,
    )

    # Nodes
    graph.add_node(schemas.PLANNER_NODE_NAME, planner.ainvoke)
    graph.add_node(schemas.EXECUTOR_NODE_NAME, executor.ainvoke)
    graph.add_node(schemas.REFLECTOR_NODE_NAME, reflector.ainvoke)
    graph.add_node(schemas.POST_PROCESS_NODE_NAME, post_process.ainvoke)
    graph.set_entry_point(schemas.PLANNER_NODE_NAME)

    return graph
