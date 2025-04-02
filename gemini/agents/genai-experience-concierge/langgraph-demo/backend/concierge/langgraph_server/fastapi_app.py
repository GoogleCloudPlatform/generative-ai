# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""FastAPI router for the langgraph-server package."""

from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from concierge.langgraph_server import schemas
import fastapi
from fastapi import responses
from langgraph_sdk import schema
import pydantic

_T = TypeVar("_T")


class ConfigModel(pydantic.BaseModel):
    """Configuration options for a call, mirroring langgraph_sdk.schema.Config."""

    tags: list[str] = []
    """A list of tags associated with the call."""
    recursion_limit: int = 25
    """The maximum recursion depth allowed for the call."""
    configurable: dict[str, Any] = {}
    """A dictionary of configurable parameters for the call."""


class CheckpointModel(pydantic.BaseModel):
    """Checkpoint configuration, mirroring langgraph_sdk.schema.Checkpoint."""

    thread_id: str
    """The ID of the thread associated with the checkpoint."""
    checkpoint_ns: str = ""
    """The namespace of the checkpoint."""
    checkpoint_id: Optional[str] = pydantic.Field(default=None, examples=[None])
    """The ID of the checkpoint."""
    checkpoint_map: dict[str, Any] = {}
    """Supposed to be optional, but langgraph raises an error if it is None."""


class GetStateCheckpointBody(pydantic.BaseModel):
    """Request body for retrieving a thread's state at a specific checkpoint."""

    checkpoint: CheckpointModel
    """The checkpoint to retrieve the state from."""
    subgraphs: bool = False
    """Whether to include subgraph states in the retrieved state."""


class UpdateStateBody(pydantic.BaseModel):
    """Request body for updating a thread's state."""

    values: Optional[Union[dict, list[dict]]] = None
    """The values to update the state with."""
    as_node: Optional[str] = None
    """The node to associate the state update with."""
    checkpoint: Optional[CheckpointModel] = None
    """The checkpoint to associate with the state update."""


class StatelessRunBody(pydantic.BaseModel):
    """Request body for running an agent without a persistent thread."""

    assistant_id: str
    """The ID of the assistant to run."""
    input: Optional[dict] = pydantic.Field(default=None, examples=[None])
    """The input to the agent."""
    command: Optional[schema.Command] = pydantic.Field(default=None, examples=[None])
    """A command to execute."""
    stream_mode: Union[schema.StreamMode, Sequence[schema.StreamMode]] = "values"
    """The streaming mode."""
    stream_subgraphs: bool = pydantic.Field(default=False, examples=[False])
    """Whether to stream subgraph outputs."""
    metadata: Optional[dict] = pydantic.Field(default=None, examples=[None])
    """Additional metadata."""
    config: Optional[ConfigModel] = None
    """Configuration settings."""
    interrupt_before: Optional[Union[schema.All, Sequence[str]]] = pydantic.Field(
        default=None,
        examples=[None],
    )
    """Interrupt execution before these nodes."""
    interrupt_after: Optional[Union[schema.All, Sequence[str]]] = pydantic.Field(
        default=None,
        examples=[None],
    )
    """Interrupt execution after these nodes."""
    multitask_strategy: Optional[schema.MultitaskStrategy] = pydantic.Field(
        default="reject",
        examples=["reject"],
        description=(
            "Strategy for handling concurrent requests to the same thread."
            " Only 'reject' is currently supported."
        ),
    )
    """Strategy for handling concurrent requests to the same thread."""

    # not supported
    feedback_keys: Optional[Sequence[str]] = []
    """Feedback keys (not supported)."""
    on_disconnect: Optional[schema.DisconnectMode] = pydantic.Field(
        default="cancel",
        examples=["cancel"],
    )
    """Disconnect mode (not supported)."""
    on_completion: Optional[schema.OnCompletionBehavior] = pydantic.Field(
        default="keep",
        examples=["keep"],
    )
    """Completion behavior (not supported)."""
    webhook: Optional[str] = None
    """Webhook URL (not supported)."""
    if_not_exists: Optional[schema.IfNotExists] = None
    """If-not-exists behavior (not supported)."""
    after_seconds: Optional[int] = None
    """Delay after seconds (not supported)."""


class ThreadRunBody(StatelessRunBody):
    """Request body for running an agent within a persistent thread."""

    checkpoint: Optional[CheckpointModel] = None
    """The checkpoint to start the thread from."""


def build_agent_router(
    agent: schemas.SerializableLangGraphAgent,
    router: fastapi.APIRouter,
) -> fastapi.APIRouter:
    """
    Builds a FastAPI router for a LangGraph agent.

    This function takes a LangGraph agent and a FastAPI router and adds the necessary routes
    to the router to interact with the agent. The routes handle graph retrieval, state management,
    and streaming execution.

    Args:
        agent: The LangGraph agent to build the router for.
        router: The FastAPI router to add the routes to.

    Returns:
        The FastAPI router with the added routes.
    """

    route_adaptor = LangGraphFastAPIRouteAdaptor(agent=agent)

    router.add_api_route(
        "/assistants/{assistant_id}/graph",
        route_adaptor.get_graph,
        methods=["GET"],
    )

    router.add_api_route(
        "/threads/{thread_id}/state/checkpoint",
        route_adaptor.get_state_checkpoint,
        methods=["POST"],
    )

    router.add_api_route(
        "/threads/{thread_id}/state",
        route_adaptor.get_state,
        methods=["GET"],
    )

    router.add_api_route(
        "/threads/{thread_id}/history",
        route_adaptor.get_state_history,
        methods=["POST"],
    )

    router.add_api_route(
        "/threads/{thread_id}/state",
        route_adaptor.update_state,
        methods=["POST"],
    )

    router.add_api_route(
        "/runs/stream",
        route_adaptor.stateless_run_stream,
        methods=["POST"],
    )

    router.add_api_route(
        "/threads/{thread_id}/runs/stream",
        route_adaptor.thread_run_stream,
        methods=["POST"],
    )

    return router


class LangGraphFastAPIRouteAdaptor:
    """
    Adaptor class for mapping LangGraph agent methods to FastAPI routes.

    This class provides methods that act as the handlers for the FastAPI routes,
    calling the corresponding methods on the LangGraph agent and handling the
    conversion of request bodies and responses.
    """

    def __init__(self, agent: schemas.SerializableLangGraphAgent):
        """
        Initializes the LangGraphFastAPIRouteAdaptor.

        Args:
            agent: The LangGraph agent to adapt.
        """

        self.agent = agent

    async def get_graph(
        self,
        assistant_id: str,
        *,
        xray: Union[int, bool] = False,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Retrieves the graph structure of the agent.

        Args:
            assistant_id: The ID of the assistant (unused, only support one assistant).
            xray: Enables or adjusts the level of graph inspection.

        Returns:
            A dictionary representing the graph structure.
        """

        del assistant_id  # unused, only support one assistant

        return self.agent.get_graph(xray=xray)

    async def get_state_checkpoint(
        self,
        thread_id: str,
        body: GetStateCheckpointBody,
    ) -> schema.ThreadState:
        """
        Retrieves the state of a thread at a specific checkpoint.

        Args:
            thread_id: The ID of the thread.
            body: The request body containing checkpoint information.

        Returns:
            The thread state at the checkpoint.
        """

        return await self.agent.get_state_checkpoint(
            thread_id=thread_id,
            checkpoint=schema.Checkpoint(
                thread_id=body.checkpoint.thread_id,
                checkpoint_ns=body.checkpoint.checkpoint_ns,
                checkpoint_id=body.checkpoint.checkpoint_id,
                checkpoint_map=body.checkpoint.checkpoint_map,
            ),
            subgraphs=body.subgraphs,
        )

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

        return await self.agent.get_state(thread_id=thread_id, subgraphs=subgraphs)

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

        return await self.agent.get_state_history(
            thread_id=thread_id,
            limit=limit,
            before=before,
        )

    async def update_state(
        self,
        thread_id: str,
        body: UpdateStateBody,
    ) -> schema.ThreadUpdateStateResponse:
        """
        Updates the state of a thread.

        Args:
            thread_id: The ID of the thread.
            body: The request body containing the state update information.

        Returns:
            The response from the state update operation.
        """

        return await self.agent.update_state(
            thread_id=thread_id,
            values=body.values,
            as_node=body.as_node,
            checkpoint=(
                schema.Checkpoint(
                    thread_id=body.checkpoint.thread_id,
                    checkpoint_ns=body.checkpoint.checkpoint_ns,
                    checkpoint_id=body.checkpoint.checkpoint_id,
                    checkpoint_map=body.checkpoint.checkpoint_map,
                )
                if body.checkpoint is not None
                else None
            ),
        )

    async def stateless_run_stream(
        self,
        body: StatelessRunBody,
    ) -> responses.StreamingResponse:
        """
        Streams the output of the agent's execution in a stateless manner.

        Args:
            body: The request body containing the run configuration.

        Returns:
            A StreamingResponse object.
        """

        stream_response = self.agent.stream(
            input=body.input,
            command=body.command,
            stream_mode=body.stream_mode,
            stream_subgraphs=body.stream_subgraphs,
            metadata=body.metadata,
            config=(
                schema.Config(
                    tags=body.config.tags,
                    recursion_limit=body.config.recursion_limit,
                    configurable=body.config.configurable,
                )
                if body.config is not None
                else None
            ),
            checkpoint=None,
            interrupt_before=body.interrupt_before,
            interrupt_after=body.interrupt_after,
        )

        return responses.StreamingResponse(
            stream_sse_chunk(stream_response=stream_response, agent=self.agent),
            media_type="text/event-stream",
        )

    async def thread_run_stream(
        self,
        thread_id: str,
        body: ThreadRunBody,
    ) -> responses.StreamingResponse:
        """
        Streams the output of the agent's execution in a threaded manner.

        Args:
            thread_id: The ID of the thread.
            body: The request body containing the run configuration.

        Returns:
            A StreamingResponse object.
        """

        if body.config is not None:
            body.config.configurable["thread_id"] = thread_id

        if isinstance(body.stream_mode, str):
            body.stream_mode = [body.stream_mode]

        stream_response = self.agent.stream(
            input=body.input,
            command=body.command,
            stream_mode=body.stream_mode,
            stream_subgraphs=body.stream_subgraphs,
            metadata=body.metadata,
            config=(
                schema.Config(
                    tags=body.config.tags,
                    recursion_limit=body.config.recursion_limit,
                    configurable=body.config.configurable,
                )
                if body.config is not None
                else None
            ),
            checkpoint=(
                schema.Checkpoint(
                    thread_id=body.checkpoint.thread_id,
                    checkpoint_ns=body.checkpoint.checkpoint_ns,
                    checkpoint_id=body.checkpoint.checkpoint_id,
                    checkpoint_map=body.checkpoint.checkpoint_map,
                )
                if body.checkpoint is not None
                else None
            ),
            interrupt_before=body.interrupt_before,
            interrupt_after=body.interrupt_after,
        )

        return responses.StreamingResponse(
            stream_sse_chunk(stream_response=stream_response, agent=self.agent),
            media_type="text/event-stream",
        )


async def async_iterator_to_list(async_iterable: AsyncIterator[_T]) -> list[_T]:
    """
    Converts an asynchronous iterator to a list.

    Args:
        async_iterable: The asynchronous iterator to convert.

    Returns:
        A list containing the elements of the asynchronous iterator.
    """

    return [element async for element in async_iterable]


async def stream_sse_chunk(
    stream_response: AsyncIterator[tuple[str, dict[str, Any]]],
    agent: schemas.SerializableLangGraphAgent,
) -> AsyncGenerator[str, None]:
    """
    Streams data from an asynchronous iterator as Server-Sent Events (SSE).

    This function takes an asynchronous iterator that yields tuples of stream mode and data chunk,
    serializes the data chunk using the agent's serializer, and formats it as an SSE chunk.

    Args:
        stream_response: The asynchronous iterator yielding stream mode and data chunk.
        agent: The LangGraph agent used for serialization.

    Yields:
        SSE formatted strings.
    """

    async for stream_mode, chunk in stream_response:
        chunk_text = agent.serde.dumps(chunk).decode()
        yield f"event: {stream_mode}\ndata: {chunk_text}\n\n"
