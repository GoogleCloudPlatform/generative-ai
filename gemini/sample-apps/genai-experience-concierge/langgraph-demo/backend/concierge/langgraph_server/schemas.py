# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Schemas and protocols for the langgraph-server package."""

from typing import Any, AsyncIterator, Literal, Optional, Protocol, Sequence, Union

from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph_sdk import schema
import pydantic


class MemoryBackendConfig(pydantic.BaseModel):
    """Configuration for an in-memory checkpoint backend."""

    type: Literal["memory"] = "memory"


class SQLiteBackendConfig(pydantic.BaseModel):
    """Configuration for a SQLite checkpoint backend."""

    type: Literal["sqlite"] = "sqlite"
    connection_string: str = ":memory:"
    """The connection string for the SQLite database. Defaults to an in-memory database."""


class PostgresBackendConfig(pydantic.BaseModel):
    """Configuration for a PostgreSQL checkpoint backend."""

    type: Literal["postgresql"] = "postgresql"
    dsn: pydantic.PostgresDsn = pydantic.Field(
        pydantic.PostgresDsn("postgresql://postgres@localhost:5432/postgres"),
        validation_alias="connection_url",
    )
    """The PostgreSQL Data Source Name (DSN)."""


CheckpointerConfig = MemoryBackendConfig | SQLiteBackendConfig | PostgresBackendConfig
"""Union type for checkpoint backend configurations."""


# pylint: disable=too-many-arguments,too-many-positional-arguments
class LangGraphAgent(Protocol):
    """Protocol defining the interface for a LangGraph agent."""

    def get_graph(
        self,
        *,
        xray: Union[int, bool] = False,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Retrieves the graph structure of the agent.

        Args:
            xray: Enables or adjusts the level of graph inspection.

        Returns:
            A dictionary representing the graph structure.
        """

    async def get_state_checkpoint(
        self,
        thread_id: str,
        checkpoint: schema.Checkpoint,
        subgraphs: bool = False,
    ) -> schema.ThreadState:
        """
        Retrieves the state of a thread at a specific checkpoint.

        Args:
            thread_id: The ID of the thread.
            checkpoint: The checkpoint to retrieve the state from.
            subgraphs: Whether to include subgraph states.

        Returns:
            The thread state at the checkpoint.
        """

    async def get_state(
        self,
        thread_id: str,
        *,
        subgraphs: bool = False,
    ) -> schema.ThreadState:
        """
        Retrieves the current state of a thread.

        Args:
            thread_id: The ID of the thread.
            subgraphs: Whether to include subgraph states.

        Returns:
            The current thread state.
        """

    async def get_state_history(
        self,
        thread_id: str,
        limit: Optional[int] = None,
        before: Optional[str] = None,
    ) -> list[schema.ThreadState]:
        """
        Retrieves the history of thread states.

        Args:
            thread_id: The ID of the thread.
            limit: The maximum number of states to retrieve.
            before: Retrieve states before this checkpoint id.

        Returns:
            A list of thread states.
        """

    async def update_state(
        self,
        thread_id: str,
        values: Optional[Union[dict, list[dict]]] = None,
        as_node: Optional[str] = None,
        checkpoint: Optional[schema.Checkpoint] = None,
    ) -> schema.ThreadUpdateStateResponse:
        """
        Updates the state of a thread.

        Args:
            thread_id: The ID of the thread.
            values: The values to update the state with.
            as_node: The node to associate the state update with.
            checkpoint: The checkpoint to associate with the state update.

        Returns:
            The response from the state update operation.
        """

    def stream(
        self,
        input: Optional[dict] = None,  # pylint: disable=redefined-builtin
        command: Optional[schema.Command] = None,
        stream_mode: Union[schema.StreamMode, Sequence[schema.StreamMode]] = "values",
        stream_subgraphs: bool = False,
        metadata: Optional[dict] = None,
        config: Optional[schema.Config] = None,
        checkpoint: Optional[schema.Checkpoint] = None,
        interrupt_before: Optional[Union[schema.All, Sequence[str]]] = None,
        interrupt_after: Optional[Union[schema.All, Sequence[str]]] = None,
    ) -> AsyncIterator[tuple[str, Any]]:
        """
        Streams the output of the agent's execution.

        Args:
            input: The input to the agent.
            command: A command to execute.
            stream_mode: The streaming mode.
            stream_subgraphs: Whether to stream subgraph outputs.
            metadata: Additional metadata.
            config: Configuration settings.
            checkpoint: The checkpoint to associate with the stream.
            interrupt_before: Interrupt execution before these nodes.
            interrupt_after: Interrupt execution after these nodes.

        Returns:
            An asynchronous iterator yielding tuples of output and metadata.
        """


# pylint: enable=too-many-arguments,too-many-positional-arguments


class SerializableLangGraphAgent(LangGraphAgent, Protocol):
    """Protocol defining a LangGraph agent that supports serialization."""

    serde: SerializerProtocol
    """The serializer protocol used by the agent."""
