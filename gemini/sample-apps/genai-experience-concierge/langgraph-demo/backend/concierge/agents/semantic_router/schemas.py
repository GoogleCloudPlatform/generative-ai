# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Schemas for the semantic router agent."""

import datetime
import enum
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
    router_model_name: str
    """The name of the Gemini model to use for routing user queries."""
    max_router_turn_history: int
    """The maximum number of turns to include in the router's context window."""


# Node names and literal types

ROUTER_NODE_NAME = "ROUTER"
"""The name of the router node in the LangGraph."""
RouterNodeTargetLiteral = Literal["ROUTER"]
"""Literal type for the router node target."""

RETAIL_NODE_NAME = "RETAIL"
"""The name of the retail node in the LangGraph."""
RetailNodeTargetLiteral = Literal["RETAIL"]
"""Literal type for the retail node target."""

CUSTOMER_SERVICE_NODE_NAME = "CUSTOMER_SERVICE"
"""The name of the customer service node in the LangGraph."""
CustomerServiceNodeTargetLiteral = Literal["CUSTOMER_SERVICE"]
"""Literal type for the customer service node target."""

POST_PROCESS_NODE_NAME = "POST_PROCESS"
"""The name of the post-processing node in the LangGraph."""
PostProcessNodeTargetLiteral = Literal["POST_PROCESS"]
"""Literal type for the post-processing node target."""

EndNodeTargetLiteral = Literal["__end__"]
"""Literal type for the end node target."""

# Router classification


class RouterTarget(enum.Enum):
    """Enumeration representing the possible targets for routing user queries."""

    CUSTOMER_SERVICE = "Customer Support Assistant"
    """Target for customer service related queries."""
    RETAIL_SEARCH = "Conversational Retail Search Assistant"
    """Target for retail search related queries."""
    UNSUPPORTED = "Unsupported"
    """Target for unsupported queries."""


class RouterClassification(pydantic.BaseModel):
    """Structured classification output for routing user queries."""

    reason: str = pydantic.Field(
        description="Reason for classifying the latest user query."
    )
    """Explanation of why the query was classified to a specific target."""
    target: RouterTarget
    """The target node to route the query to."""

    model_config = pydantic.ConfigDict(
        json_schema_extra={"propertyOrdering": ["reason", "target"]}
    )
    """Configuration to specify the ordering of properties in the JSON schema."""


# LangGraph models


class Turn(TypedDict, total=False):
    """
    Represents a single turn in a conversation.

    Attributes:
        id: Unique identifier for the turn.
        created_at: Timestamp of when the turn was created.
        user_input: The user's input in this turn.
        response: The agent's response in this turn, if any.
        router_classification: The router classification for this turn, if any.
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

    router_classification: RouterClassification | None
    """The router classification for this turn, if any."""

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
