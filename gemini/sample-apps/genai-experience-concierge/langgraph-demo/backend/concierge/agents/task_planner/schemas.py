# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Schemas for the task planner agent."""

# pylint: disable=line-too-long

import datetime
from typing import Literal, TypedDict
import uuid

from google.genai import types as genai_types  # type: ignore[import-untyped]
import pydantic

# Agent config settings


class AgentConfig(pydantic.BaseModel):
    """Configuration settings for the agent, including project, region, and model details."""

    project: str
    """The Google Cloud project ID."""
    region: str
    """The Google Cloud region where the agent is deployed."""
    planner_model_name: str
    """The name of the Gemini model to use for planning."""
    executor_model_name: str
    """The name of the Gemini model to use for executing tasks."""
    reflector_model_name: str
    """The name of the Gemini model to use for reflecting on the plan and results."""


# Node names and literal types

REFLECTOR_NODE_NAME = "REFLECTOR"
"""The name of the reflector node in the LangGraph."""
ReflectorNodeTargetLiteral = Literal["REFLECTOR"]
"""Literal type for the reflector node target."""

EXECUTOR_NODE_NAME = "EXECUTOR"
"""The name of the executor node in the LangGraph."""
ExecutorNodeTargetLiteral = Literal["EXECUTOR"]
"""Literal type for the executor node target."""

PLANNER_NODE_NAME = "PLANNER"
"""The name of the planner node in the LangGraph."""
PlannerNodeTargetLiteral = Literal["PLANNER"]
"""Literal type for the planner node target."""

POST_PROCESS_NODE_NAME = "POST_PROCESS"
"""The name of the post-processing node in the LangGraph."""
PostProcessNodeTargetLiteral = Literal["POST_PROCESS"]
"""Literal type for the post-processing node target."""

EndNodeTargetLiteral = Literal["__end__"]
"""Literal type for the end node target."""

# langgraph models


class Task(pydantic.BaseModel):
    """An individual task with a goal and result."""

    goal: str = pydantic.Field(
        description="The description and goal of this step in the plan.",
    )
    """The description and goal of this step in the plan."""

    result: str | None = pydantic.Field(
        default=None,
        description=(
            "The result of this step determined by the plan executor."
            " Always set this field to None"
        ),
    )
    """The result of this step determined by the plan executor. Always set this field to None."""


class Plan(pydantic.BaseModel):
    """A step-by-step sequential plan."""

    goal: str = pydantic.Field(description="High level goal for plan to help user.")
    """High level goal for plan to help user."""
    tasks: list[Task] = pydantic.Field(
        description=(
            "A list of individual tasks that will be executed in sequence before responding to the user."
            " As the task gets more complex, you can add more steps."
        ),
    )
    """A list of individual tasks that will be executed in sequence before responding to the user. As the task gets more complex, you can add more steps."""


class Response(pydantic.BaseModel):
    """Response to send to the user."""

    response: str
    """The response message to send to the user."""


class PlanOrRespond(pydantic.BaseModel):
    """Action to perform. Either respond to user or generate a research plan."""

    action: Response | Plan = pydantic.Field(
        description="The next action can either be a direct response to the user or generate a new plan if you need to think more and use tools."
    )
    """The next action can either be a direct response to the user or generate a new plan if you need to think more and use tools."""


# LangGraph models


class Turn(TypedDict, total=False):
    """
    Represents a single turn in a conversation.

    Attributes:
        id: Unique identifier for the turn.
        created_at: Timestamp of when the turn was created.
        user_input: The user's input in this turn.
        response: The agent's response in this turn, if any.
        plan: The agent's last generated plan for this turn, if any.
        messages: A list of Gemini content messages associated with this turn.
    """

    id: uuid.UUID
    """Unique identifier for the turn."""

    created_at: datetime.datetime
    """Timestamp of when the turn was created."""

    user_input: str
    """The user's input for this turn."""

    response: str
    """The agent's response for this turn, if any."""

    plan: Plan | None
    """The agent's last generated plan for this turn, if any."""

    messages: list[genai_types.Content]
    """List of Gemini Content objects representing the conversation messages in this turn."""


class GraphSession(TypedDict, total=False):
    """
    Represents the complete state of a conversation session.

    Attributes:
        id: Unique identifier for the session.
        created_at: Timestamp of when the session was created.
        current_turn: The current turn in the session, if any.
        turns: A list of all turns in the session.
    """

    id: uuid.UUID
    """Unique identifier for the session."""

    created_at: datetime.datetime
    """Timestamp of when the session was created."""

    current_turn: Turn | None
    """The current conversation turn."""

    turns: list[Turn]
    """List of all conversation turns in the session."""
