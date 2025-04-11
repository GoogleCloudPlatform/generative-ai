# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Utilities to load LangGraph checkpointers from a supported config."""

import logging

import aiosqlite
from concierge.langgraph_server import schemas
from langgraph.checkpoint import base, memory
from langgraph.checkpoint.postgres import aio as postgres_aio
from langgraph.checkpoint.sqlite import aio as sqlite_aio
import psycopg
from psycopg.rows import DictRow
import psycopg_pool

logger = logging.getLogger(__name__)


def load_checkpointer(
    backend_config: schemas.CheckpointerConfig,
) -> base.BaseCheckpointSaver:
    """
    Loads a checkpoint saver based on the provided backend configuration.

    This function takes a CheckpointerConfig object and returns a BaseCheckpointSaver instance,
    which can be a MemorySaver, AsyncSqliteSaver, or AsyncPostgresSaver, depending on the
    backend configuration.

    Args:
        backend_config: The configuration for the checkpoint backend.

    Returns:
        A BaseCheckpointSaver instance.

    Raises:
        ValueError: If an unknown backend type is provided.
    """

    checkpointer: base.BaseCheckpointSaver

    match backend_config:
        case schemas.MemoryBackendConfig():
            # Create checkpointer
            checkpointer = memory.MemorySaver()

        case schemas.SQLiteBackendConfig():
            # Open sqlite connection
            connection = aiosqlite.connect(backend_config.connection_string)

            # Create checkpointer
            checkpointer = sqlite_aio.AsyncSqliteSaver(conn=connection)

        case schemas.PostgresBackendConfig():
            # Open postgres connection pool
            connection_pool = psycopg_pool.AsyncConnectionPool(
                conninfo=backend_config.dsn.unicode_string(),
                connection_class=psycopg.AsyncConnection[DictRow],
                kwargs={"autocommit": True},
                open=False,
            )

            # Create checkpointer
            checkpointer = postgres_aio.AsyncPostgresSaver(conn=connection_pool)

        case _:
            raise ValueError(f"Unknown backend type: {type(backend_config)}")

    return checkpointer


async def setup_checkpointer(checkpointer: base.BaseCheckpointSaver) -> None:
    """
    Sets up the checkpoint saver, performing any necessary initialization.

    This function takes a BaseCheckpointSaver instance and performs any setup operations
    required for the specific type of checkpoint saver. For example, it opens the connection
    pool for Postgres and sets up the database schema for SQLite.

    Args:
        checkpointer: The checkpoint saver to set up.
    """

    match checkpointer:
        case memory.MemorySaver():
            pass

        case postgres_aio.AsyncPostgresSaver():
            if isinstance(checkpointer.conn, psycopg_pool.AsyncConnectionPool):
                await checkpointer.conn.open()

            await checkpointer.setup()

        case sqlite_aio.AsyncSqliteSaver():
            await checkpointer.setup()

        case _:
            logger.warning(
                f"Ignoring unknown checkpoint saver type: {type(checkpointer)}"
            )


async def cleanup_checkpointer(checkpointer: base.BaseCheckpointSaver) -> None:
    """
    Cleans up the checkpoint saver, releasing any resources.

    This function takes a BaseCheckpointSaver instance and performs any cleanup operations
    required for the specific type of checkpoint saver. For example, it closes the connection
    pool for Postgres and closes the connection for SQLite.

    Args:
        checkpointer: The checkpoint saver to clean up.
    """

    match checkpointer:
        case memory.MemorySaver():
            pass

        case postgres_aio.AsyncPostgresSaver():
            await checkpointer.conn.close()

        case sqlite_aio.AsyncSqliteSaver():
            await checkpointer.conn.close()

        case _:
            logger.warning(
                f"Ignoring unknown checkpoint saver type: {type(checkpointer)}"
            )
