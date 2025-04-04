# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Schemas for the task planner agent nodes."""

# pylint: disable=line-too-long

from typing import TypedDict

from concierge import schemas
import pydantic


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


class PlannerTurn(schemas.BaseTurn, total=False):
    """Represents a single turn in a conversation."""

    plan: Plan | None
    """The agent's last generated plan for this turn, if any."""


class PlannerState(TypedDict, total=False):
    """Session state for planner agent nodes."""

    current_turn: PlannerTurn | None
    """The current conversation turn."""

    turns: list[PlannerTurn]
    """List of all conversation turns in the session."""


class TaskPlannerConfig(pydantic.BaseModel):
    """Configuration settings for the task planner node."""

    project: str
    region: str = "us-central1"
    planner_model_name: str = "gemini-2.0-flash-001"
    executor_model_name: str = "gemini-2.0-flash-001"
    reflector_model_name: str = "gemini-2.0-flash-001"
