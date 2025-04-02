# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Runtime settings for the LangGraph agent server."""

from typing import Self

from concierge.langgraph_server import schemas
import pydantic
import pydantic_settings


class RuntimeSettings(pydantic_settings.BaseSettings):
    """Runtime settings for the LangGraph agents."""

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

    @pydantic.model_validator(mode="after")
    def ensure_cymbal_dataset_resources(self) -> Self:
        """Ensure that the Cymbal dataset resources are set."""

        if self.cymbal_embedding_model_uri is None:
            self.cymbal_embedding_model_uri = (
                f"{self.project}.{self.cymbal_dataset}.text_embedding"
            )

        if self.cymbal_inventory_table_uri is None:
            self.cymbal_inventory_table_uri = (
                f"{self.project}.{self.cymbal_dataset}.cymbal_inventory"
            )

        if self.cymbal_products_table_uri is None:
            self.cymbal_products_table_uri = (
                f"{self.project}.{self.cymbal_dataset}.cymbal_product"
            )

        if self.cymbal_stores_table_uri is None:
            self.cymbal_stores_table_uri = (
                f"{self.project}.{self.cymbal_dataset}.cymbal_store"
            )

        return self
