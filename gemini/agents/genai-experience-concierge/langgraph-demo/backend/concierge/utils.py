# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Utilities for Gen AI SDK."""

import asyncio
import inspect
import logging
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Mapping,
    ParamSpec,
    TypeVar,
)

from concierge import schemas
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from langgraph import graph
import pydantic
import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def load_graph(
    schema: type,
    nodes: list[schemas.Node],
    entry_point: schemas.Node,
) -> graph.StateGraph:
    """Load a state graph from a list of nodes.

    Note: This function only works with "edgeless" graphs,
    which use the Command object to specify the next node to trnasition to.
    """

    state_graph = graph.StateGraph(state_schema=schema)

    for node in nodes:
        state_graph.add_node(node.name, node.fn)

    state_graph.set_entry_point(entry_point.name)

    return state_graph


def load_user_content(current_turn: schemas.BaseTurn) -> genai_types.Content:
    """Load user input from current turn into a Content object."""

    user_input = current_turn.get("user_input")
    assert user_input is not None, "user input must be set"

    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=user_input)],
    )

    return user_content


def is_retryable_error(exception: BaseException) -> bool:
    """
    Determines if a given exception is considered retryable.

    This function checks if the provided exception is an API error with a retryable HTTP status code
    (429, 502, 503, 504) or a connection error.

    Args:
        exception: The exception to evaluate.

    Returns:
        True if the exception is retryable, False otherwise.
    """

    if isinstance(exception, genai_errors.APIError):
        return exception.code in [429, 502, 503, 504]
    if isinstance(exception, requests.exceptions.ConnectionError):
        return True
    return False


def default_retry(func: Callable[P, T]) -> Callable[P, T]:
    """Defines a default retry strategy for Gemini invocation, with exponential backoff."""

    return retry(
        retry=retry_if_exception(is_retryable_error),
        wait=wait_exponential(min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )(func)


# pylint: disable=too-many-arguments,too-many-positional-arguments
async def generate_content_stream(
    model: str,
    contents: list[genai_types.Content],
    config: genai_types.GenerateContentConfig,
    client: genai.Client,
    max_recursion_depth: int = 3,
    fn_map: dict[str, Callable] | None = None,
) -> AsyncGenerator[genai_types.Content, None]:
    """
    Streams generated content from a Gemini model, handling function calls within the stream.

    This function iteratively generates content from a Gemini model, processing function calls
    encountered during generation. It executes these function calls asynchronously and feeds
    their results back to the model for continued generation.

    Args:
        model: The name of the Gemini model to use.
        contents: The list of Content objects representing the conversation history.
        config: The GenerateContentConfig for the model.
        client: The Gemini client.
        max_recursion_depth: The maximum depth of recursive function calls to prevent infinite loops.
        fn_map: A mapping of function names to their corresponding callable functions.

    Yields:
        Content objects representing the generated content, including text and function call responses.
    """  # pylint: disable=line-too-long

    fn_map = fn_map or {}

    if max_recursion_depth < 0:
        logger.warning("Maximum depth reached, stopping generation.")
        return

    response: AsyncIterator[genai_types.GenerateContentResponse] = (
        await client.aio.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        )
    )

    # iterate over chunk in main request
    async for chunk in response:
        if chunk.candidates is None or chunk.candidates[0].content is None:
            logger.warning("no candidates or content, skipping chunk.")
            continue

        # yield current chunk content (assume only one candidate)
        content = chunk.candidates[0].content
        yield content

        # if any function calls:
        # - execute each in parallel
        # - then call generate after responses are gathered
        if chunk.function_calls:
            # create asyncio tasks to execute each function call
            tasks = list[asyncio.Task[dict[str, Any]]]()
            for function_call in chunk.function_calls:
                if function_call.name is None:
                    logger.warning("skipping function call without name")
                    continue

                if function_call.name not in fn_map:
                    raise RuntimeError(
                        f"Function not provided in fn_map: {function_call.name}"
                    )

                func = fn_map[function_call.name]
                kwargs = function_call.args or {}

                tasks.append(asyncio.create_task(run_function_async(func, kwargs)))

            fn_results = await asyncio.gather(*tasks)

            # create and yield content from function responses
            fn_response_content = genai_types.Content(
                role="user",
                parts=[
                    genai_types.Part.from_function_response(
                        name=fn_call.name, response=fn_result
                    )
                    for fn_call, fn_result in zip(chunk.function_calls, fn_results)
                ],
            )
            yield fn_response_content

            # continue generation and yield resulting content
            async for content in generate_content_stream(
                model=model,
                contents=contents
                + [
                    content.model_copy(deep=True),
                    fn_response_content.model_copy(deep=True),
                ],
                config=config,
                client=client,
                max_recursion_depth=max_recursion_depth - 1,
                fn_map=fn_map,
            ):
                yield content


# pylint: enable=too-many-arguments,too-many-positional-arguments


async def run_function_async(
    function: Callable[..., pydantic.BaseModel | Awaitable[pydantic.BaseModel]],
    function_kwargs: Mapping[str, Any],
) -> dict[str, str | dict]:
    """
    Runs a function asynchronously and wraps the results for google-genai FunctionResponse.

    This function executes a given function asynchronously, handling both synchronous and asynchronous functions.
    Note: Sync functions are made asynchronous by running in the default threadpool executor so any sync functions should be thread-safe.

    Args:
        function: The function to execute.
        function_kwargs: The arguments to pass to the function.

    Returns:
        A dictionary containing the function's result or an error message.
    """  # pylint: disable=line-too-long

    try:
        if inspect.iscoroutinefunction(function):
            fn_result = await function(**function_kwargs)
        else:
            loop = asyncio.get_running_loop()
            fn_result = await loop.run_in_executor(
                None,
                lambda kwargs: function(**kwargs),
                function_kwargs,
            )

        return {"result": fn_result.model_dump(mode="json")}

    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"error": str(e)}
