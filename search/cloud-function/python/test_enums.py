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
This module contains unit tests for the custom enums defined in enums.py.

It tests the functionality of FlexibleIntEnum and its subclasses,
ensuring they handle various input types correctly.
"""

from enums import EngineChunkType, EngineDataType, SummaryType
import pytest


def test_flexible_int_enum_from_int() -> None:
    """Test creation of FlexibleIntEnum subclasses from integer values."""
    assert EngineDataType(0) == EngineDataType.UNSTRUCTURED
    assert EngineDataType(1) == EngineDataType.STRUCTURED
    assert EngineDataType(2) == EngineDataType.WEBSITE
    assert EngineDataType(3) == EngineDataType.BLENDED


def test_flexible_int_enum_from_string() -> None:
    """Test creation of FlexibleIntEnum subclasses from string values."""
    assert EngineDataType("UNSTRUCTURED") == EngineDataType.UNSTRUCTURED
    assert EngineDataType("STRUCTURED") == EngineDataType.STRUCTURED
    assert EngineDataType("WEBSITE") == EngineDataType.WEBSITE
    assert EngineDataType("BLENDED") == EngineDataType.BLENDED


def test_flexible_int_enum_case_insensitive() -> None:
    """Test case-insensitive creation of FlexibleIntEnum subclasses from strings."""
    assert EngineDataType("unstructured") == EngineDataType.UNSTRUCTURED
    assert EngineDataType("Structured") == EngineDataType.STRUCTURED


def test_flexible_int_enum_from_enum_member() -> None:
    """Test creation of FlexibleIntEnum subclasses from existing enum members."""
    assert EngineDataType(EngineDataType.UNSTRUCTURED) == EngineDataType.UNSTRUCTURED
    assert EngineChunkType(EngineChunkType.CHUNK) == EngineChunkType.CHUNK
    assert SummaryType(SummaryType.VERTEX_AI_SEARCH) == SummaryType.VERTEX_AI_SEARCH


def test_flexible_int_enum_invalid_value() -> None:
    """Test handling of invalid values for FlexibleIntEnum subclasses."""
    with pytest.raises(ValueError):
        EngineDataType("INVALID")
    with pytest.raises(ValueError):
        EngineDataType(999)
    with pytest.raises(ValueError):
        EngineDataType(-1)
    with pytest.raises(ValueError):
        EngineDataType(3.14)
    with pytest.raises(ValueError):
        EngineDataType(None)


def test_engine_chunk_type_enum() -> None:
    """Test creation and comparison of EngineChunkType enum values."""
    assert EngineChunkType(0) == EngineChunkType.DOCUMENT_WITH_SNIPPETS
    assert (
        EngineChunkType("DOCUMENT_WITH_EXTRACTIVE_SEGMENTS")
        == EngineChunkType.DOCUMENT_WITH_EXTRACTIVE_SEGMENTS
    )
    assert EngineChunkType("chunk") == EngineChunkType.CHUNK


def test_summary_type_enum() -> None:
    """Test creation and comparison of SummaryType enum values."""
    assert SummaryType(0) == SummaryType.NONE
    assert SummaryType("VERTEX_AI_SEARCH") == SummaryType.VERTEX_AI_SEARCH
    assert (
        SummaryType("generate_grounded_answers")
        == SummaryType.GENERATE_GROUNDED_ANSWERS
    )


def test_enum_to_int() -> None:
    """Test conversion of enum values to integers."""
    assert int(EngineDataType.UNSTRUCTURED) == 0
    assert int(EngineChunkType.DOCUMENT_WITH_EXTRACTIVE_SEGMENTS) == 1
    assert int(SummaryType.GEMINI) == 3


def test_enum_to_string() -> None:
    """Test conversion of enum values to strings."""
    assert str(EngineDataType.STRUCTURED) == "STRUCTURED"
    assert str(EngineChunkType.CHUNK) == "CHUNK"
    assert str(SummaryType.VERTEX_AI_SEARCH) == "VERTEX_AI_SEARCH"


def test_enum_name_and_value() -> None:
    """Test access to enum names and values."""
    assert EngineDataType.UNSTRUCTURED.name == "UNSTRUCTURED"
    assert EngineDataType.UNSTRUCTURED.value == 0
    assert (
        EngineChunkType.DOCUMENT_WITH_EXTRACTIVE_SEGMENTS.name
        == "DOCUMENT_WITH_EXTRACTIVE_SEGMENTS"
    )
    assert EngineChunkType.DOCUMENT_WITH_EXTRACTIVE_SEGMENTS.value == 1


if __name__ == "__main__":
    pytest.main()
