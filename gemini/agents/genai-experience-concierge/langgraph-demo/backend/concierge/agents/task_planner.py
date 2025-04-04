# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Task planner agent for the Concierge demo."""

from concierge import settings, utils
from concierge.langgraph_server import langgraph_agent
from concierge.nodes import chat, save_turn
from concierge.nodes.task_planning import executor, planner, reflector, schemas


def load_agent(
    runtime_settings: settings.RuntimeSettings,
) -> langgraph_agent.LangGraphAgent:
    """Loads the task planner agent for the Concierge demo."""

    planner_node = planner.build_planner_node(
        node_name="planner",
        plan_processor_node_name="executor",
        response_processor_node_name="save-turn",
    )

    executor_node = executor.build_executor_node(
        node_name="executor",
        next_node="reflector",
    )

    reflector_node = reflector.build_reflector_node(
        node_name="reflector",
        executor_node_name="executor",
        response_processor_node_name="save-turn",
    )

    save_turn_node = save_turn.build_save_turn_node(node_name="save-turn")

    gemini_agent = langgraph_agent.LangGraphAgent(
        state_graph=utils.load_graph(
            schema=chat.ChatState,
            nodes=[planner_node, executor_node, reflector_node, save_turn_node],
            entry_point=planner_node,
        ),
        default_configurable={
            "planner_config": schemas.TaskPlannerConfig(
                project=runtime_settings.project,
                region=runtime_settings.region,
                planner_model_name=runtime_settings.planner_model_name,
                executor_model_name=runtime_settings.executor_model_name,
                reflector_model_name=runtime_settings.reflector_model_name,
            )
        },
        checkpointer_config=runtime_settings.checkpointer,
    )

    return gemini_agent
