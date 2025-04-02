# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Node to reflect on the current plan and either respond or generate a new plan."""

import logging
from typing import Literal

from concierge import schemas as concierge_schemas
from concierge.nodes.task_planning import schemas
from concierge.nodes.task_planning.ops import reflect_plan
from langchain_core.runnables import config as lc_config
from langgraph import types as lg_types
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)


def build_reflector_node(
    node_name: str = "reflector",
    executor_node_name: str = "executor",
    response_processor_node_name: str = "save-turn",
) -> concierge_schemas.Node:
    """Builds a LangGraph node to reflect on the executed plan and respond or create a new plan."""

    NextNodeT = Literal[executor_node_name, response_processor_node_name]  # type: ignore

    async def ainvoke(
        state: schemas.PlannerState,
        config: lc_config.RunnableConfig,
    ) -> lg_types.Command[NextNodeT]:
        """
        Asynchronously reflects on the executed plan and determines the next action.

        This function takes the current conversation state, which includes the executed plan,
        and uses the `reflect_plan` function to analyze the results and decide whether to
        generate a new plan or provide a direct response. It then updates the conversation state
        and directs the flow to the appropriate next node.

        Runtime configuration should be passed in `config.configurable.planner_config`.

        Args:
            state: The current state of the conversation session, including the executed plan.
            config: The LangChain RunnableConfig containing agent-specific configurations.

        Returns:
            A Command object that specifies the next node to transition to and the
            updated conversation state. The state includes the updated plan or response.

        Raises:
            AssertionError: If the plan is not generated or not fully executed before reflection.
            TypeError: If the plan reflection action is of an unsupported type.
        """

        agent_config = schemas.TaskPlannerConfig.model_validate(
            config["configurable"].get("planner_config", {})
        )

        stream_writer = get_stream_writer()

        current_turn = state.get("current_turn")
        assert current_turn is not None, "current turn must be set"

        plan = current_turn.get("plan")
        assert plan is not None, "plan must be set"

        user_input = current_turn.get("user_input")
        assert user_input is not None, "user input must be set"

        assert all(
            task.result is not None for task in plan.tasks
        ), "Must execute each plan task before reflection."

        plan_reflection = await reflect_plan.reflect_plan(
            user_input=user_input,
            executed_plan=plan,
            project=agent_config.project,
            region=agent_config.region,
            model_name=agent_config.reflector_model_name,
        )

        next_node = None
        match plan_reflection.action:
            case schemas.Plan():
                next_node = executor_node_name

                # Ensure results aren't set
                for task in plan_reflection.action.tasks:
                    task.result = None

                # Add new tasks from plan reflection
                plan.tasks += plan_reflection.action.tasks
                current_turn["plan"] = plan

                stream_writer({"plan": plan.model_dump(mode="json")})

            case schemas.Response():
                next_node = response_processor_node_name

                # Update turn response
                current_turn["response"] = plan_reflection.action.response

                stream_writer({"response": current_turn["response"]})
            case _:  # never
                raise TypeError(
                    f"Unsupported plan reflection action: {type(plan_reflection.action)}"
                )

        return lg_types.Command(
            update=schemas.PlannerState(current_turn=current_turn),
            goto=next_node,
        )

    return concierge_schemas.Node(name=node_name, fn=ainvoke)
