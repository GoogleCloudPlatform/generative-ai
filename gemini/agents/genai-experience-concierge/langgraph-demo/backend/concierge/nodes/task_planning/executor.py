# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Node to execute the current plan and update the conversation state."""

import logging
from typing import Literal

from concierge import schemas as concierge_schemas
from concierge.nodes.task_planning import schemas
from concierge.nodes.task_planning.ops import execute_plan
from langchain_core.runnables import config as lc_config
from langgraph import types as lg_types
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)


def build_executor_node(
    node_name: str = "executor",
    next_node: str = "reflector",
) -> concierge_schemas.Node:
    """Builds a LangGraph node to execute a plan's tasks and update the conversation state."""

    async def ainvoke(
        state: schemas.PlannerState,
        config: lc_config.RunnableConfig,
    ) -> lg_types.Command[Literal[next_node]]:
        """
        Asynchronously executes a plan's tasks and updates the conversation state.

        This function takes the current conversation state, which includes a plan,
        and executes each task within that plan.
        It utilizes the `execute_plan` function to process each task, updating the
        plan with the results as it goes.
        The function also streams the executed tasks to the user via the stream writer.

        Runtime configuration should be passed in `config.configurable.planner_config`.

        Args:
            state: The current state of the conversation session, including the plan to execute.
            config: The LangChain RunnableConfig containing agent-specific configurations.

        Returns:
            A Command object that specifies the next node to transition to (reflector) and the
            updated conversation state. The state includes the plan with executed tasks.

        Raises:
            AssertionError: If the plan is not generated before execution.
        """

        stream_writer = get_stream_writer()

        planner_config = schemas.TaskPlannerConfig.model_validate(
            config["configurable"].get("planner_config", {})
        )

        current_turn = state.get("current_turn")
        assert current_turn is not None, "current turn must be set"

        plan = current_turn.get("plan")
        assert plan is not None, "plan must be set"

        async for idx, executed_task in execute_plan.execute_plan(
            plan=plan,
            project=planner_config.project,
            region=planner_config.region,
            model_name=planner_config.executor_model_name,
        ):
            # update state with executed task
            plan.tasks[idx] = executed_task

            stream_writer({"executed_task": executed_task.model_dump(mode="json")})

        current_turn["plan"] = plan

        return lg_types.Command(
            update=schemas.PlannerState(current_turn=current_turn),
            goto=next_node,
        )

    return concierge_schemas.Node(name=node_name, fn=ainvoke)
