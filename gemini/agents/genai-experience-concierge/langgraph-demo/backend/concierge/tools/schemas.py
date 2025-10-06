# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Schemas for the function calling tools."""

from typing import Optional

from concierge import schemas as concierge_schemas
import pydantic


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


class FunctionCallingTurn(concierge_schemas.BaseTurn, total=False):
    """Represents a single turn in a conversation."""

    user_latitude: float | None
    """The current user's latitude, if available."""

    user_longitude: float | None
    """The current user's longitude, if available."""


class FunctionCallingConfig(pydantic.BaseModel):
    """Configuration settings for the router node."""

    project: str
    """The Google Cloud project ID."""
    region: str
    """The Google Cloud region."""
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
