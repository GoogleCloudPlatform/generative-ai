# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""
Node to save a turn to the conversation history
and reset the current turn for the LangGraph agent server.
"""

from typing import Literal, TypedDict

from concierge import schemas
from langgraph import types as lg_types


class SaveTurnState(TypedDict):
    """Stores the active turn and conversation history."""

    current_turn: schemas.BaseTurn
    turns: list[schemas.BaseTurn]


def build_save_turn_node(
    node_name: str = "save-turn",
    next_node: str = "__end__",
) -> schemas.Node:
    """Builds a LangGraph node to save the current turn to the conversation history."""

    async def ainvoke(
        state: SaveTurnState,
    ) -> lg_types.Command[Literal[next_node]]:
        """
        Saves the current turn to the conversation history and resets the current turn.

        This node takes the current conversation state, validates that the current turn
        and its response are set, adds the completed turn to the conversation history,
        and resets the current turn.

        Args:
            state: The current state of the conversation session.
            config: The LangChain RunnableConfig (unused in this function).

        Returns:
            A Command object specifying the end of the graph execution
            and the updated conversation state.
        """

        current_turn = state.get("current_turn")

        assert current_turn is not None, "Current turn must be set."
        assert (
            "response" in current_turn and current_turn["response"] is not None
        ), "Response from current turn must be set."

        turns = state.get("turns", []) + [current_turn]

        return lg_types.Command(update={"current_turn": None, "turns": turns})

    return schemas.Node(name=node_name, fn=ainvoke)
