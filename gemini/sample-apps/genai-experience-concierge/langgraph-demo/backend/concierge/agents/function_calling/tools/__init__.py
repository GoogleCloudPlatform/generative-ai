# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

from typing import Callable, NamedTuple

from concierge.agents.function_calling import schemas
from concierge.agents.function_calling.tools import (
    find_inventory,
    find_products,
    find_stores,
)
from google.genai import types as genai_types


class FunctionSpec(NamedTuple):
    """A named tuple representing an LLM-callable function specification."""

    fd: genai_types.FunctionDeclaration
    callable: Callable


def load_function_specs(
    turn: schemas.Turn,
    agent_config: schemas.AgentConfig,
) -> list[FunctionSpec]:
    """Load a list of function specs containing function declarations and callable handlers."""

    user_latitude = turn.get("user_latitude")
    user_longitude = turn.get("user_longitude")

    assert not (
        (user_latitude is None) ^ (user_longitude is None)
    ), "Latitude and longitude must both be defined or both null"

    user_coordinate = None
    if user_latitude is not None and user_longitude is not None:
        user_coordinate = schemas.Coordinate(
            latitude=user_latitude,
            longitude=user_longitude,
        )

    find_stores_handler = find_stores.generate_find_stores_handler(
        project=agent_config.project,
        cymbal_dataset_location=agent_config.cymbal_dataset_location,
        cymbal_stores_table_uri=agent_config.cymbal_stores_table_uri,
        cymbal_inventory_table_uri=agent_config.cymbal_inventory_table_uri,
        user_coordinate=user_coordinate,
    )
    find_stores_fd = find_stores.find_stores_fd
    assert (
        find_stores_fd.name is not None
    ), "Function name must be set for automatic function calling"

    find_products_handler = find_products.generate_find_products_handler(
        project=agent_config.project,
        cymbal_dataset_location=agent_config.cymbal_dataset_location,
        cymbal_products_table_uri=agent_config.cymbal_products_table_uri,
        cymbal_inventory_table_uri=agent_config.cymbal_inventory_table_uri,
        cymbal_embedding_model_uri=agent_config.cymbal_embedding_model_uri,
    )
    find_products_fd = find_products.find_products_fd
    assert (
        find_products_fd.name is not None
    ), "Function name must be set for automatic function calling"

    find_inventory_handler = find_inventory.generate_find_inventory_handler(
        project=agent_config.project,
        cymbal_dataset_location=agent_config.cymbal_dataset_location,
        cymbal_inventory_table_uri=agent_config.cymbal_inventory_table_uri,
    )
    find_inventory_fd = find_inventory.find_inventory_fd
    assert (
        find_inventory_fd.name is not None
    ), "Function name must be set for automatic function calling"

    return [
        FunctionSpec(fd=find_products_fd, callable=find_products_handler),
        FunctionSpec(fd=find_stores_fd, callable=find_stores_handler),
        FunctionSpec(fd=find_inventory_fd, callable=find_inventory_handler),
    ]
