# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Runtime settings for the LangGraph agent server."""

from concierge.agents import (
    function_calling,
    gemini_chat,
    gemini_chat_with_guardrails,
    semantic_router,
    task_planner,
)
from concierge.langgraph_server import schemas
import pydantic
import pydantic_settings


class AgentServerConfig(pydantic_settings.BaseSettings):
    """Runtime settings for the LangGraph agent server."""

    checkpointer: schemas.CheckpointerConfig = pydantic.Field(
        default_factory=schemas.MemoryBackendConfig
    )

    # must be specified and exist to correctly run.
    project: str = "unspecified"
    cymbal_dataset: str = "cymbal_retail"
    cymbal_dataset_location: str = "US"

    # optional explicit table uris. will default to the standard table names if not provided
    cymbal_embedding_model_uri: str | None = None
    cymbal_inventory_table_uri: str | None = None
    cymbal_products_table_uri: str | None = None
    cymbal_stores_table_uri: str | None = None

    # sane default values, only configure as needed
    region: str = "us-central1"
    chat_model_name: str = "gemini-2.0-flash-001"
    function_calling_model_name: str = "gemini-2.0-flash-001"
    router_model_name: str = "gemini-2.0-flash-001"
    guardrail_model_name: str = "gemini-2.0-flash-001"
    planner_model_name: str = "gemini-2.0-flash-001"
    executor_model_name: str = "gemini-2.0-flash-001"
    reflector_model_name: str = "gemini-2.0-flash-001"
    max_router_turn_history: int = 3

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="concierge_",
        case_sensitive=False,
        env_nested_delimiter="__",
    )


settings = AgentServerConfig()

checkpointer_config = settings.checkpointer

gemini_config = gemini_chat.AgentConfig(
    project=settings.project,
    region=settings.region,
    chat_model_name=settings.chat_model_name,
)

guardrail_config = gemini_chat_with_guardrails.AgentConfig(
    project=settings.project,
    region=settings.region,
    chat_model_name=settings.chat_model_name,
    guardrail_model_name=settings.guardrail_model_name,
)

fc_config = function_calling.AgentConfig(
    project=settings.project,
    region=settings.region,
    chat_model_name=settings.function_calling_model_name,
    cymbal_dataset_location=settings.cymbal_dataset_location,
    cymbal_embedding_model_uri=(
        settings.cymbal_embedding_model_uri
        or f"{settings.project}.{settings.cymbal_dataset}.text_embedding"
    ),
    cymbal_inventory_table_uri=(
        settings.cymbal_inventory_table_uri
        or f"{settings.project}.{settings.cymbal_dataset}.cymbal_inventory"
    ),
    cymbal_products_table_uri=(
        settings.cymbal_products_table_uri
        or f"{settings.project}.{settings.cymbal_dataset}.cymbal_product"
    ),
    cymbal_stores_table_uri=(
        settings.cymbal_stores_table_uri
        or f"{settings.project}.{settings.cymbal_dataset}.cymbal_store"
    ),
)

router_config = semantic_router.AgentConfig(
    project=settings.project,
    region=settings.region,
    chat_model_name=settings.chat_model_name,
    router_model_name=settings.router_model_name,
    max_router_turn_history=settings.max_router_turn_history,
)

planner_config = task_planner.AgentConfig(
    project=settings.project,
    region=settings.region,
    planner_model_name=settings.planner_model_name,
    executor_model_name=settings.executor_model_name,
    reflector_model_name=settings.reflector_model_name,
)
