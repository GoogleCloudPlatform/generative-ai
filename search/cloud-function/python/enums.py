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
from enum import IntEnum


class FlexibleIntEnum(IntEnum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                return cls[value.upper()]
            except KeyError:
                pass
        elif isinstance(value, int):
            try:
                return cls(value)
            except ValueError:
                pass
        raise ValueError(f"{value} is not a valid {cls.__name__}")


class EngineDataType(FlexibleIntEnum):
    UNSTRUCTURED = 0
    STRUCTURED = 1
    WEBSITE = 2
    BLENDED = 3


class EngineChunkType(FlexibleIntEnum):
    DOCUMENT_WITH_SNIPPETS = 0
    DOCUMENT_WITH_EXTRACTIVE_SEGMENTS = 1
    CHUNK = 2


class SummaryType(FlexibleIntEnum):
    NONE = 0
    VERTEX_AI_SEARCH = 1
    GENERATE_GROUNDED_ANSWERS = 2
    GEMINI = 3
