# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Schemas for the function calling agent."""

import datetime
from typing import Literal, Optional, TypedDict
import uuid

from google.genai import types as genai_types  # type: ignore[import-untyped]
import pydantic

# Agent config settings


class AgentConfig(pydantic.BaseModel):
    """
    Configuration settings for the agent, including project, region, model, and data locations.
    """

    project: str
    """The Google Cloud project ID."""
    region: str
    """The Google Cloud region where the agent is deployed."""
    chat_model_name: str
    """The name of the Gemini chat model to use."""
    cymbal_dataset_location: str
    """Location of the Cymbal dataset."""
    cymbal_products_table_uri: str
    """URI of the Cymbal products table."""
    cymbal_stores_table_uri: str
    """URI of the Cymbal stores table."""
    cymbal_inventory_table_uri: str
    """URI of the Cymbal inventory table."""
    cymbal_embedding_model_uri: str
    """URI of the Cymbal embedding model."""


# Node names and literal types

CHAT_NODE_NAME = "CHAT"
"""The name of the chat node in the LangGraph."""

POST_PROCESS_NODE_NAME = "POST_PROCESS"
"""The name of the post-processing node in the LangGraph."""

PostProcessNodeTargetLiteral = Literal["POST_PROCESS"]
"""Literal type for the post-processing node target."""

EndNodeTargetLiteral = Literal["__end__"]
"""Literal type for the end node target."""

# DB Models


class Store(pydantic.BaseModel):
    """Represents a store with its details."""

    id: str
    """Unique identifier for the store."""
    name: str
    """Name of the store."""
    url: str
    """URL of the store's website."""
    street_address: str
    """Street address of the store."""
    city: str
    """City where the store is located."""
    state: str
    """State where the store is located."""
    zip_code: int
    """ZIP code of the store."""
    country: str
    """Country where the store is located."""
    phone_number: str
    """Phone number of the store."""
    latitude: float
    """Latitude of the store's location."""
    longitude: float
    """Longitude of the store's location."""


class Product(pydantic.BaseModel):
    """Represents a product with its details."""

    id: str
    """Unique identifier for the product."""
    name: str
    """Name of the product."""
    url: str
    """URL of the product's page."""
    description: str
    """Description of the product."""
    brand: Optional[str] = None
    """Brand of the product (optional)."""
    category: str
    """Category of the product."""
    available: bool
    """Availability status of the product."""
    list_price: float
    """List price of the product."""
    sale_price: Optional[float] = None
    """Sale price of the product (optional)."""
    currency: str = "usd"
    """Currency of the product's price."""


class Inventory(pydantic.BaseModel):
    """Represents the inventory of a product in a store."""

    store_id: str
    """Identifier of the store."""
    product_id: str
    """Identifier of the product."""
    value: int = 0
    """Quantity of the product in the store's inventory."""


# Tool return types


class StoreSearchResult(pydantic.BaseModel):
    """Represents the result of a store search."""

    stores: list[Store] = []
    """List of stores matching the search criteria."""
    query: Optional[str] = None
    """The search query used."""
    error: Optional[str] = None
    """Error message, if any."""


class ProductSearchResult(pydantic.BaseModel):
    """Represents the result of a product search."""

    products: list[Product] = []
    """List of products matching the search criteria."""
    query: Optional[str] = None
    """The search query used."""
    error: Optional[str] = None
    """Error message, if any."""


class InventorySearchResult(pydantic.BaseModel):
    """Represents the result of an inventory search."""

    inventory: Optional[Inventory] = None
    """The inventory information for the product in the store."""
    query: Optional[str] = None
    """The search query used."""
    error: Optional[str] = None
    """Error message, if any."""


# LangGraph models


class Turn(TypedDict, total=False):
    """
    Represents a single turn in a conversation.

    Attributes:
        id: Unique identifier for the turn.
        created_at: Timestamp of when the turn was created.
        user_input: The user's input in this turn.
        response: The agent's response in this turn, if any.
        user_latitude: The user's latitude in this turn, if any.
        user_longitude: The user's longitude in this turn, if any
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

    user_latitude: float | None
    """The user's latitude for this turn, if any."""

    user_longitude: float | None
    """The user's longitude for this turn, if any."""

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
