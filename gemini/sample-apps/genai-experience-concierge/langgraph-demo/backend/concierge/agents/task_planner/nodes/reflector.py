# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
from typing import Literal

from concierge.agents.task_planner import schemas
from concierge.agents.task_planner.ops import reflect_plan
from langchain_core.runnables import config as lc_config
from langgraph import types as lg_types
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)


async def ainvoke(
    state: schemas.GraphSession,
    config: lc_config.RunnableConfig,
) -> lg_types.Command[
    Literal[schemas.EXECUTOR_NODE_TARGET_LITERAL, schemas.PLANNER_NODE_TARGET_LITERAL]
]:
    """
    Asynchronously reflects on the executed plan and determines the next action.

    This function takes the current conversation state, which includes the executed plan, and uses
    the `reflect_plan` function to analyze the results and decide whether to generate a new plan
    or provide a direct response. It then updates the conversation state and directs the flow
    to the appropriate next node (executor or planner).

    Args:
        state: The current state of the conversation session, including the executed plan.
        config: The LangChain RunnableConfig containing agent-specific configurations.

    Returns:
        A Command object that specifies the next node to transition to (executor or planner) and the
        updated conversation state. The state includes the updated plan or response.

    Raises:
        AssertionError: If the plan is not generated or not fully executed before reflection.
        TypeError: If the plan reflection action is of an unsupported type.
    """

    agent_config = schemas.AgentConfig.model_validate(
        config["configurable"].get("agent_config", {})
    )

    stream_writer = get_stream_writer()

    current_turn = state.get("current_turn")
    assert current_turn is not None, "current turn must be set"

    user_input = current_turn.get("user_input")
    assert user_input is not None, "user input must be set"

    plan = current_turn.get("plan")
    assert plan is not None, "plan must be set"

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
    if isinstance(plan_reflection.action, schemas.Plan):
        next_node = schemas.EXECUTOR_NODE_NAME

        # Ensure results aren't set
        for task in plan_reflection.action.tasks:
            task.result = None

        # Add new tasks from plan reflection
        plan.tasks += plan_reflection.action.tasks
        current_turn["plan"] = plan

        stream_writer({"plan": plan.model_dump(mode="json")})

    elif isinstance(plan_reflection.action, schemas.Response):
        next_node = schemas.POST_PROCESS_NODE_NAME

        # Update turn response
        current_turn["response"] = plan_reflection.action.response

        stream_writer({"response": current_turn["response"]})
    else:  # never
        raise TypeError(
            "Unsupported plan reflection action: %s", type(plan_reflection.action)
        )

    return lg_types.Command(
        update=schemas.GraphSession(current_turn=current_turn),
        goto=next_node,
    )
