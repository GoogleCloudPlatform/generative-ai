# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility module providing decorator for chain implementations.

This module contains a decorator for implementing chains with
Python-based orchestration, as shown in app/patterns/custom_rag_qa/chain.py.

The decorators help standardize chain implementations and provide common functionality
like event streaming and tracing.

When using frameworks like LangGraph or CrewAI that provide their own orchestration, this file
can be safely removed.
"""
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import inspect
from typing import Any, AsyncGenerator, Callable, List, Union

from app.utils.output_types import OnChatModelStreamEvent, OnToolEndEvent
from langchain_core.messages import AIMessage
from langchain_core.runnables.utils import Input
from tqdm import tqdm
from traceloop.sdk import TracerWrapper
from traceloop.sdk.decorators import aworkflow


class CustomChain:
    """A custom chain class that wraps a callable function."""

    def __init__(self, func: Callable):
        """Initialize the CustomChain with a callable function."""
        self.func = func

    async def astream_events(self, *args: Any, **kwargs: Any) -> AsyncGenerator:
        """
        Asynchronously stream events from the wrapped function.
        Applies Traceloop workflow decorator if Traceloop SDK is initialized.
        """

        if hasattr(TracerWrapper, "instance"):
            func = aworkflow()(self.func)
        else:
            func = self.func

        async_gen = func(*args, **kwargs)

        # Traceloop "aworkflow" decorator returns a co-routine which should be awaited
        if inspect.iscoroutine(async_gen):
            async_gen = await async_gen

        async for event in async_gen:
            yield event.model_dump()

    def invoke(self, *args: Any, **kwargs: Any) -> AIMessage:
        """
        Invoke the wrapped function and process its events.
        Returns an AIMessage with content and relative tool calls.
        """
        events = self.func(*args, **kwargs)
        response_content = ""
        tool_calls = []
        for event in events:
            if isinstance(event, OnChatModelStreamEvent):
                if not isinstance(event.data.chunk.content, str):
                    raise ValueError("Chunk content must be a string")
                response_content += event.data.chunk.content
            elif isinstance(event, OnToolEndEvent):
                tool_calls.append(event.data.model_dump())
        return AIMessage(
            content=response_content, additional_kwargs={"tool_calls_data": tool_calls}
        )

    def batch(
        self,
        inputs: List[Input],
        *args: Any,
        max_workers: Union[int, None] = None,
        **kwargs: Any
    ) -> List[AIMessage]:
        """
        Invoke the wrapped function and process its events in batch.
        Returns a List of AIMessage with content and relative tool calls.
        """
        predicted_messages = []
        with ThreadPoolExecutor(max_workers) as pool:
            for response in tqdm(
                pool.map(self.invoke, inputs, *args, **kwargs), total=len(inputs)
            ):
                predicted_messages.append(response)
        return predicted_messages

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Make the CustomChain instance callable, invoking the wrapped function."""
        return self.func(*args, **kwargs)


def custom_chain(func: Callable) -> CustomChain:
    """
    Decorator function that wraps a callable in a CustomChain instance.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return CustomChain(wrapper)
