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
"""
This module defines custom enums used in the Vertex AI Search client.

These enums provide type-safe options for configuring the search engine,
data types, and summary generation.
"""

from enum import IntEnum
from typing import Any, Union


class FlexibleIntEnum(IntEnum):
    """
    A flexible IntEnum that allows creation from various input types.

    This class extends IntEnum to provide more flexible instantiation,
    supporting string inputs (case-insensitive) and existing enum members.
    """

    @classmethod
    def _missing_(cls, value: Any) -> Union["FlexibleIntEnum", None]:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        elif isinstance(value, int):
            try:
                return next(member for member in cls if member.value == value)
            except StopIteration:
                pass
        return None

    def __str__(self) -> str:
        return self.name


class EngineDataType(FlexibleIntEnum):
    """Enum representing the type of data in the search engine."""

    UNSTRUCTURED = 0
    STRUCTURED = 1
    WEBSITE = 2
    BLENDED = 3


class EngineChunkType(FlexibleIntEnum):
    """Enum representing the type of chunking used in the search engine."""

    DOCUMENT_WITH_SNIPPETS = 0
    DOCUMENT_WITH_EXTRACTIVE_SEGMENTS = 1
    CHUNK = 2


class SummaryType(FlexibleIntEnum):
    """Enum representing the type of summary generation used."""

    NONE = 0
    VERTEX_AI_SEARCH = 1
    GENERATE_GROUNDED_ANSWERS = 2
    GEMINI = 3
