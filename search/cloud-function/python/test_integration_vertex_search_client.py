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
Integration tests for the VertexAISearchClient.

This module contains integration tests that interact with the actual
Vertex AI Search API. These tests require proper configuration of
environment variables and access to the Vertex AI Search service.
"""

from collections.abc import Generator
import os

import pytest
from vertex_ai_search_client import VertexAISearchClient, VertexAISearchConfig

# Load environment variables
PROJECT_ID = os.getenv("PROJECT_ID", "your-project")
LOCATION = os.getenv("LOCATION", "global")
DATA_STORE_ID = os.getenv("DATA_STORE_ID", "your-data-store")
ENGINE_DATA_TYPE = os.getenv("ENGINE_DATA_TYPE", "UNSTRUCTURED")
ENGINE_CHUNK_TYPE = os.getenv("ENGINE_CHUNK_TYPE", "CHUNK")
SUMMARY_TYPE = os.getenv("SUMMARY_TYPE", "VERTEX_AI_SEARCH")


@pytest.fixture(scope="module")
def vertex_ai_search_client() -> Generator[VertexAISearchClient, None, None]:
    """
    Fixture to create and yield a VertexAISearchClient instance for testing.

    This fixture creates a VertexAISearchClient instance using the
    environment variables and yields it for use in tests. The client
    is shared across all tests in the module for efficiency.

    Yields:
        VertexAISearchClient: An instance of the VertexAISearchClient for testing.
    """
    config = VertexAISearchConfig(
        project_id=PROJECT_ID,
        location=LOCATION,
        data_store_id=DATA_STORE_ID,
        engine_data_type="UNSTRUCTURED",
        engine_chunk_type="DOCUMENT_WITH_EXTRACTIVE_SEGMENTS",
        summary_type="VERTEX_AI_SEARCH",
    )
    client = VertexAISearchClient(config)
    yield client


def test_search_integration(client: VertexAISearchClient) -> None:
    """
    Test the search functionality of VertexAISearchClient with the actual API.

    This test performs a search using the VertexAISearchClient and verifies
    that the results have the expected structure and content types.

    Args:
        vertex_ai_search_client (VertexAISearchClient): The client instance to test.
    """
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


def test_unstructured_summary() -> None:
    """
    Test VertexAISearchClient with unstructured data and summary generation.

    This test creates a new VertexAISearchClient instance with specific
    settings for unstructured data and summary generation, then performs
    a search to verify the results.
    """
    config = VertexAISearchConfig(
        project_id=PROJECT_ID,
        location=LOCATION,
        data_store_id=DATA_STORE_ID,
        engine_data_type="UNSTRUCTURED",
        engine_chunk_type="DOCUMENT_WITH_EXTRACTIVE_SEGMENTS",
        summary_type="VERTEX_AI_SEARCH",
    )
    client = VertexAISearchClient(config)
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
