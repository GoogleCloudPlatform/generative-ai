# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Schemas for the guardrail chat agent."""

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
    chat_model_name: str
    """The name of the Gemini chat model to use for generating responses."""
    guardrail_model_name: str
    """The name of the Gemini model to use for guardrail classification."""


# Node names and literal types

CHAT_NODE_NAME = "CHAT"
"""The name of the chat node in the LangGraph."""
ChatNodeTargetLiteral = Literal["CHAT"]
"""Literal type for the chat node target."""

GUARDRAILS_NODE_NAME = "GUARDRAILS"
"""The name of the guardrails node in the LangGraph."""
GuardrailsNodeTargetLiteral = Literal["GUARDRAILS"]
"""Literal type for the guardrails node target."""

POST_PROCESS_NODE_NAME = "POST_PROCESS"
"""The name of the post-processing node in the LangGraph."""
PostProcessNodeTargetLiteral = Literal["POST_PROCESS"]
"""Literal type for the post-processing node target."""

EndNodeTargetLiteral = Literal["__end__"]
"""Literal type for the end node target."""

# Guardrail models


class RequestClassification(pydantic.BaseModel):
    """
    Represents the classification of a user request by the guardrails system.

    Attributes:
        blocked: Indicates whether the request should be blocked.
        reason: The reason for the classification decision.
        guardrail_response: A fallback message to be displayed to the user if the request is blocked.
    """  # pylint: disable=line-too-long

    blocked: bool = pydantic.Field(
        description="The classification decision on whether the request should be blocked.",
    )
    """Boolean indicating whether the request should be blocked."""
    reason: str = pydantic.Field(
        description="Reason why the response was given the classification value.",
    )
    """Explanation of why the request was classified as blocked or allowed."""
    guardrail_response: str = pydantic.Field(
        description=(
            "Guardrail fallback message if the response is blocked."
            " Should be safe to surface to users."
        ),
    )
    """A safe message to display to the user if their request is blocked."""


# LangGraph models


class Turn(TypedDict, total=False):
    """
    Represents a single turn in a conversation.

    Attributes:
        id: Unique identifier for the turn.
        created_at: Timestamp of when the turn was created.
        user_input: The user's input in this turn.
        response: The agent's response in this turn, if any.
        classification: The guardrail classification for this turn, if any.
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

    classification: RequestClassification
    """The guardrail classification for this turn, if any."""

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
