# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Implementation of LangGraphAgent given a StateGraph."""

import logging
from typing import Any, AsyncGenerator, Optional, Sequence, Union, cast

from concierge.langgraph_server import checkpoint_saver, schemas
from langchain_core.runnables import config as lc_config
from langgraph import graph
from langgraph import types as lg_types
from langgraph.checkpoint import base
from langgraph.checkpoint.serde import jsonplus
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph_sdk import schema

logger = logging.getLogger(__name__)


# pylint: disable=too-many-arguments,too-many-positional-arguments
class LangGraphAgent:
    """
    A class that wraps a LangGraph StateGraph and provides methods to interact with it.

    This class initializes a LangGraph agent with a state graph, agent configuration,
    serializer, and checkpointer configuration. It provides methods to retrieve the graph
    structure, get and update the graph's state, and stream the graph's execution.
    """

    def __init__(
        self,
        state_graph: graph.StateGraph,
        serde: Optional[SerializerProtocol] = None,
        default_configurable: Optional[dict] = None,
        checkpointer_config: Optional[schemas.CheckpointerConfig] = None,
    ):
        """
        Initializes the LangGraphAgent.

        Args:
            state_graph: The LangGraph StateGraph to wrap.
            agent_config: Optional agent configuration.
            serde: Optional serializer protocol.
            checkpointer_config: Optional checkpointer configuration.
        """
        self.state_graph = state_graph

        default_configurable = default_configurable or {}
        self.config = lc_config.RunnableConfig(configurable=default_configurable)

        self.checkpointer = (
            checkpoint_saver.load_checkpointer(checkpointer_config)
            if checkpointer_config is not None
            else None
        )

        self.compiled_graph = self.state_graph.compile(checkpointer=self.checkpointer)

        if isinstance(self.checkpointer, base.BaseCheckpointSaver):
            self.serde = self.checkpointer.serde
        elif serde is not None:
            self.serde = serde
        else:
            # fall back to jsonplus serializer in case a checkpointer is not available
            self.serde = jsonplus.JsonPlusSerializer()

    async def setup(self) -> None:
        """Sets up the checkpointer if it exists."""
        if self.checkpointer:
            await checkpoint_saver.setup_checkpointer(checkpointer=self.checkpointer)

    def get_graph(
        self, *, xray: Union[int, bool] = False
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Retrieves the graph structure of the agent.

        Args:
            xray: Enables or adjusts the level of graph inspection.

        Returns:
            A dictionary representing the graph structure.
        """
        return self.compiled_graph.get_graph(xray=xray).to_json()

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
        configurable = {**checkpoint, "thread_id": thread_id}
        runnable_config = lc_config.RunnableConfig(configurable=configurable)
        runnable_config = lc_config.merge_configs(self.config, runnable_config)

        state_snapshot = await self.compiled_graph.aget_state(
            config=runnable_config,
            subgraphs=subgraphs,
        )

        return _state_snapshot_to_thread_state(snapshot=state_snapshot)

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
        runnable_config = lc_config.RunnableConfig(
            configurable={"thread_id": thread_id}
        )
        runnable_config = lc_config.merge_configs(self.config, runnable_config)

        state_snapshot = await self.compiled_graph.aget_state(
            config=runnable_config,
            subgraphs=subgraphs,
        )

        return _state_snapshot_to_thread_state(snapshot=state_snapshot)

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
        thread_config = lc_config.RunnableConfig(configurable={"thread_id": thread_id})
        checkpoint_config = (
            lc_config.RunnableConfig(configurable={"checkpoint_id": before})
            if before is not None
            else None
        )
        checkpoint_config = lc_config.merge_configs(self.config, checkpoint_config)

        state_snapshot_list = [
            _state_snapshot_to_thread_state(snapshot=snapshot)
            async for snapshot in self.compiled_graph.aget_state_history(
                config=thread_config,
                limit=limit,
                before=checkpoint_config,
            )
        ]

        return state_snapshot_list

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
        checkpoint_dict = (
            cast(dict[str, Any], checkpoint) if checkpoint is not None else {}
        )
        checkpoint_dict["thread_id"] = thread_id

        runnable_config = lc_config.ensure_config({"configurable": checkpoint_dict})
        runnable_config = lc_config.merge_configs(self.config, runnable_config)

        checkpoint_config = await self.compiled_graph.aupdate_state(
            config=runnable_config,
            values=values,
            as_node=as_node,
        )

        return schema.ThreadUpdateStateResponse(
            checkpoint=_checkpoint_from_runnable_config(checkpoint_config)
        )

    async def stream(
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
    ) -> AsyncGenerator[tuple[str, Any], None]:
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
        # ensure valid runnable config by merging params
        runnable_config = lc_config.ensure_config(
            (
                {
                    "tags": config.get("tags", []),
                    "configurable": config.get("configurable", {}),
                    "metadata": metadata or {},
                }
                if config
                else None
            ),
        )
        # checkpoint fields takes precedence over config
        runnable_config["configurable"].update(checkpoint or {})

        # only insert recursion limit if it is configured.
        if config is not None and "recursion_limit" in config:
            runnable_config["recursion_limit"] = runnable_config["recursion_limit"]

        runnable_config = lc_config.merge_configs(self.config, runnable_config)

        stream_input: Optional[Union[dict, schema.Command]] = input
        if command is not None:
            stream_input = command

        stream_response = self.compiled_graph.astream(
            input=stream_input,
            config=runnable_config,
            # langgraph_sdk stream modes aren't currently compatible. must cast to langgraph types
            stream_mode=cast(
                lg_types.StreamMode | list[lg_types.StreamMode], stream_mode
            ),
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            subgraphs=stream_subgraphs,
        )

        # if stream_mode is a sequence instead of a single string, yield includes mode per chunk
        if not isinstance(stream_mode, str):
            async for chunk_stream_mode, chunk in stream_response:
                yield (chunk_stream_mode, chunk)

        async for chunk in stream_response:
            yield (cast(str, stream_mode), chunk)


# pylint: enable=too-many-arguments,too-many-positional-arguments


def _checkpoint_from_runnable_config(
    config: lc_config.RunnableConfig,
) -> schema.Checkpoint:
    """
    Creates a Checkpoint object from a RunnableConfig.

    Args:
        config: The RunnableConfig containing checkpoint information.

    Returns:
        A Checkpoint object.
    """

    return schema.Checkpoint(
        thread_id=config["configurable"]["thread_id"],
        checkpoint_ns=config["configurable"].get("checkpoint_ns", ""),
        checkpoint_id=config["configurable"].get("checkpoint_id"),
        checkpoint_map=config["configurable"].get("checkpoint_map", {}),
    )


def _state_snapshot_to_thread_state(
    snapshot: lg_types.StateSnapshot,
) -> schema.ThreadState:
    """
    Converts a StateSnapshot to a ThreadState.

    Args:
        snapshot: The StateSnapshot to convert.

    Returns:
        A ThreadState object.
    """

    return schema.ThreadState(
        values=snapshot.values,
        next=snapshot.next,
        checkpoint=_checkpoint_from_runnable_config(snapshot.config),
        metadata=cast(schema.Json, snapshot.metadata or {}),
        created_at=snapshot.created_at,
        parent_checkpoint=(
            _checkpoint_from_runnable_config(snapshot.parent_config)
            if snapshot.parent_config is not None
            else None
        ),
        tasks=[_pregel_task_to_thread_task(task) for task in snapshot.tasks],
    )


def _pregel_task_to_thread_task(task: lg_types.PregelTask) -> schema.ThreadTask:
    """
    Converts a PregelTask to a ThreadTask.

    Args:
        task: The PregelTask to convert.

    Returns:
        A ThreadTask object.
    """

    state = None

    if isinstance(task.state, lg_types.StateSnapshot):
        # note: possible cyclical recursion
        state = _state_snapshot_to_thread_state(task.state)

    # don't recursively fetch history
    if isinstance(task.state, dict):
        pass

    return schema.ThreadTask(
        id=task.id,
        name=task.name,
        error=str(task.error) if task.error is not None else None,
        interrupts=[
            schema.Interrupt(
                value=interrupt.value,
                when=interrupt.when,
                resumable=interrupt.resumable,
                ns=list(interrupt.ns) if interrupt.ns else None,
            )
            for interrupt in task.interrupts
        ],
        checkpoint=None,  # already included in snapshot, not sure why this is here???
        state=state,
        result=task.result,
    )
