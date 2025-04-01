# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

from concierge.agents.task_planner import schemas
from langchain_core.runnables import config as lc_config
from langgraph import types as lg_types


def ainvoke(
    state: schemas.GraphSession,
    config: lc_config.RunnableConfig,
) -> lg_types.Command[schemas.EndNodeTargetLiteral]:
    """
    Asynchronously invokes the post-processing node to finalize the current conversation turn.

    This function takes the current conversation state, validates that the current turn and its response are set,
    adds the completed turn to the conversation history, and resets the current turn. This effectively concludes
    the processing of the current user input and prepares the session for the next input.

    Args:
        state: The current state of the conversation session.
        config: The LangChain RunnableConfig (unused in this function).

    Returns:
        A Command object specifying the end of the graph execution and the updated conversation state.
    """

    del config  # unused

    current_turn = state.get("current_turn")

    assert current_turn is not None, "Current turn must be set."
    assert (
        current_turn["response"] is not None
    ), "Response from current turn must be set."

    turns = state.get("turns", []) + [current_turn]

    return lg_types.Command(update=schemas.GraphSession(current_turn=None, turns=turns))
