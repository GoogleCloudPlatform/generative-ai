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
import os

from enums import EngineChunkType, EngineDataType, SummaryType
import pytest
from vertex_search_client import VertexSearchClient

# Load environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
DATA_STORE_ID = os.getenv("DATA_STORE_ID")
ENGINE_DATA_TYPE = os.getenv("ENGINE_DATA_TYPE", 0)
ENGINE_CHUNK_TYPE = os.getenv("ENGINE_CHUNK_TYPE", 1)
SUMMARY_TYPE = os.getenv("SUMMARY_TYPE", 1)


@pytest.fixture(scope="module")
def client():
    return VertexSearchClient(
        project_id=PROJECT_ID,
        location=LOCATION,
        data_store_id=DATA_STORE_ID,
        engine_data_type=ENGINE_DATA_TYPE,
        engine_chunk_type=ENGINE_CHUNK_TYPE,
        summary_type=SUMMARY_TYPE,
    )


def test_search_integration(client):
    # Perform a search
    query = "test query"
    results = client.search(query)

    # Check the structure of the results
    assert "simplified_results" in results
    assert isinstance(results["simplified_results"], list)

    if results["simplified_results"]:
        first_result = results["simplified_results"][0]
        assert "metadata" in first_result
        assert "page_content" in first_result

    # Check for other expected fields
    assert "total_size" in results
    assert isinstance(results["total_size"], int)

    if "summary" in results:
        assert "summary_text" in results["summary"]


# Test with different engine types and settings.
# You must have these configured already...
def test_unstructured_summary():
    client = VertexSearchClient(
        project_id=PROJECT_ID,
        location=LOCATION,
        data_store_id=DATA_STORE_ID,
        engine_data_type=EngineDataType.UNSTRUCTURED,
        engine_chunk_type=EngineChunkType.DOCUMENT_WITH_EXTRACTIVE_SEGMENTS,
        summary_type=SummaryType.VERTEX_AI_SEARCH,
    )
    results = client.search("What is the name of the company?")
    # Check the structure of the results
    assert "simplified_results" in results
    assert isinstance(results["simplified_results"], list)

    if results["simplified_results"]:
        first_result = results["simplified_results"][0]
        assert "metadata" in first_result
        assert "page_content" in first_result


if __name__ == "__main__":
    pytest.main()
