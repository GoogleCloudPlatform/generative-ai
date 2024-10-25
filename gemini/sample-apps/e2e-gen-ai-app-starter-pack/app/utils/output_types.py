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

from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from types import GeneratorType
from typing import Any, AsyncGenerator, Callable, Dict, List, Literal, Union
import uuid

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.runnables.utils import Input
from pydantic import BaseModel, Field
from tqdm import tqdm
from traceloop.sdk import TracerWrapper
from traceloop.sdk.decorators import workflow


class BaseCustomChainEvent(BaseModel):
    """Base class for custom chain events."""

    name: str = "custom_chain_event"

    class Config:
        """Allow extra fields in the model."""

        extra = "allow"


class OnToolStartEvent(BaseCustomChainEvent):
    """Event representing the start of a tool execution."""

    event: Literal["on_tool_start"] = "on_tool_start"
    input: Dict = {}
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ToolData(BaseModel):
    """Data structure for tool input and output."""

    input: Dict = {}
    output: ToolMessage


class OnToolEndEvent(BaseCustomChainEvent):
    """Event representing the end of a tool execution."""

    event: Literal["on_tool_end"] = "on_tool_end"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: ToolData


class ChatModelStreamData(BaseModel):
    """Data structure for chat model stream chunks."""

    chunk: AIMessageChunk


class OnChatModelStreamEvent(BaseCustomChainEvent):
    """Event representing a chunk of streamed chat model output."""

    event: Literal["on_chat_model_stream"] = "on_chat_model_stream"
    data: ChatModelStreamData


class Event(BaseModel):
    """Generic event structure."""

    event: str = "data"
    data: dict


class EndEvent(BaseModel):
    """Event representing the end of a stream."""

    event: Literal["end"] = "end"


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
            func = workflow()(self.func)
        else:
            func = self.func

        gen: GeneratorType = func(*args, **kwargs)

        for event in gen:
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
