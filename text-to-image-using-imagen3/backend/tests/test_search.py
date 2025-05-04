# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the search controller and service."""

import base64
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from src.controller.search import router
from src.model.search import (
    ImageGenerationResult,
    CustomImageResult,
)
from src.service.search import ImagenSearchService

# Create a test client for the FastAPI app
client = TestClient(router)


@pytest.fixture(scope="function", name="mock_genai_client")
def fixture_mock_genai_client():
    """Provides a mock google.genai Client."""
    mock_client = MagicMock()
    mock_response = types.GenerateImagesResponse()

    # Create mock generated images with base64 encoded placeholder image data
    mock_image = types.GeneratedImage()
    mock_image.enhanced_prompt = "Mock enhanced prompt"
    mock_image.image = types.Image()
    mock_image.image.gcs_uri = "gs://mock_bucket/mock_image.png"
    mock_image.image.image_bytes = b"mock_image_bytes"  # Must be bytes
    mock_image.image.mime_type = "image/png"
    mock_response.generated_images = [
        mock_image,
        mock_image,
        mock_image,
        mock_image,
    ]

    mock_client.models.generate_images.return_value = mock_response
    return mock_client


@pytest.fixture(scope="function", name="mock_imagen_search_service")
def fixture_mock_imagen_search_service(mock_genai_client):
    """Provides a mock ImagenSearchService with a mock genai client."""
    service = ImagenSearchService()
    service.client = mock_genai_client  # Inject the mock client
    return service


class TestSearchController:
    """Tests for the /api/search endpoint."""

    def test_search_endpoint(self, monkeypatch, mock_imagen_search_service):
        # Mock the ImagenSearchService to avoid actual API calls
        # Mock the google.auth.default to avoid authentication issues
        with monkeypatch.context() as m:  # use a context for clarity
            mock_client_class = MagicMock(
                return_value=mock_imagen_search_service.client
            )
            m.setattr(
                "src.controller.search.ImagenSearchService",
                lambda: mock_imagen_search_service,
            )
            m.setattr(
                "src.service.search.google.auth.default",
                lambda: (None, "test_project_id"),
            )
            m.setattr(
                "src.service.search.google.genai.Client", mock_client_class
            )

            search_term = "test search term"
            response = client.post("/api/search", json={"term": search_term})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

        for image_data in data:
            assert image_data["enhancedPrompt"] == "Mock enhanced prompt"
            assert (
                image_data["image"]["gcsUri"]
                == "gs://mock_bucket/mock_image.png"
            )
            assert image_data["image"]["mimeType"] == "image/png"
            assert image_data["image"]["encodedImage"] == base64.b64encode(
                b"mock_image_bytes"
            ).decode("utf-8")
            # other assertions based on the model


class TestImagenSearchService:
    """Tests for the ImagenSearchService class."""

    def test_imagen_search_service(
        self, monkeypatch, mock_imagen_search_service
    ):

        # Mock the google.auth.default to avoid authentication issues
        with monkeypatch.context() as m:  # use a context for clarity
            mock_client_class = MagicMock(
                return_value=mock_imagen_search_service.client
            )
            m.setattr(
                "src.service.search.google.auth.default",
                lambda: (None, "test_project_id"),
            )
            m.setattr(
                "src.service.search.google.genai.Client", mock_client_class
            )

            search_term = "test search term"
            results = mock_imagen_search_service.generate_images(search_term)

        assert isinstance(results, list)
        assert len(results) == 4  #  Number of mock images
        assert all(
            isinstance(result, ImageGenerationResult) for result in results
        )
        mock_client_class.assert_called_once()

        for result in results:
            assert isinstance(result.image, CustomImageResult)
            assert result.image.encoded_image == base64.b64encode(
                b"mock_image_bytes"
            ).decode("utf-8")
