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

from typing import Annotated, Any, List, Literal, Optional, Union

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field


class InputChat(BaseModel):
    """Represents the input for a chat session."""

    messages: List[
        Annotated[
            Union[HumanMessage, AIMessage, ToolMessage], Field(discriminator="type")
        ]
    ] = Field(
        ..., description="The chat messages representing the current conversation."
    )
    user_id: str = ""
    session_id: str = ""


class Input(BaseModel):
    """Wrapper class for InputChat."""

    input: InputChat


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: Union[int, float]
    text: Optional[str] = ""
    run_id: str
    log_type: Literal["feedback"] = "feedback"


def default_serialization(obj: Any) -> Any:
    """
    Default serialization for LangChain objects.
    Converts BaseModel instances to dictionaries.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump()
