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
Integration tests for the VertexSearchClient.

This module contains integration tests that interact with the actual
Vertex AI Search API. These tests require proper configuration of
environment variables and access to the Vertex AI Search service.
"""

import os
from typing import Generator

import pytest
from vertex_search_client import VertexSearchClient, VertexSearchConfig

# Load environment variables
PROJECT_ID = os.getenv("PROJECT_ID", "your-project")
LOCATION = os.getenv("LOCATION", "global")
DATA_STORE_ID = os.getenv("DATA_STORE_ID", "your-data-store")
ENGINE_DATA_TYPE = os.getenv("ENGINE_DATA_TYPE", "UNSTRUCTURED")
ENGINE_CHUNK_TYPE = os.getenv("ENGINE_CHUNK_TYPE", "CHUNK")
SUMMARY_TYPE = os.getenv("SUMMARY_TYPE", "VERTEX_AI_SEARCH")


@pytest.fixture(scope="module")
def vertex_search_client() -> Generator[VertexSearchClient, None, None]:
    """
    Fixture to create and yield a VertexSearchClient instance for testing.

    This fixture creates a VertexSearchClient instance using the
    environment variables and yields it for use in tests. The client
    is shared across all tests in the module for efficiency.

    Yields:
        VertexSearchClient: An instance of the VertexSearchClient for testing.
    """
    config = VertexSearchConfig(
        project_id=PROJECT_ID,
        location=LOCATION,
        data_store_id=DATA_STORE_ID,
        engine_data_type="UNSTRUCTURED",
        engine_chunk_type="DOCUMENT_WITH_EXTRACTIVE_SEGMENTS",
        summary_type="VERTEX_AI_SEARCH",
    )
    client = VertexSearchClient(config)
    yield client


def test_search_integration(vertex_search_client: VertexSearchClient) -> None:
    """
    Test the search functionality of VertexSearchClient with the actual API.

    This test performs a search using the VertexSearchClient and verifies
    that the results have the expected structure and content types.

    Args:
        vertex_search_client (VertexSearchClient): The client instance to test.
    """
    # Perform a search
    query = "test query"
    results = vertex_search_client.search(query)

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
    Test VertexSearchClient with unstructured data and summary generation.

    This test creates a new VertexSearchClient instance with specific
    settings for unstructured data and summary generation, then performs
    a search to verify the results.
    """
    config = VertexSearchConfig(
        project_id=PROJECT_ID,
        location=LOCATION,
        data_store_id=DATA_STORE_ID,
        engine_data_type="UNSTRUCTURED",
        engine_chunk_type="DOCUMENT_WITH_EXTRACTIVE_SEGMENTS",
        summary_type="VERTEX_AI_SEARCH",
    )
    client = VertexSearchClient(config)
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
