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
from io import BytesIO
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from google.genai import types
from PIL import Image as PIL_Image

from src.controller.search import router
from src.model.search import (
    CreateSearchRequest,
    ImageGenerationResult,
    CustomImageResult,
)
from src.service.search import ImagenSearchService

client = TestClient(router)


def create_minimal_image_bytes(image_format="PNG") -> bytes:
    """Creates bytes for a 1x1 pixel image."""
    img = PIL_Image.new("RGB", (1, 1), color="red")
    buffer = BytesIO()
    img.save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.fixture(scope="function", name="mock_genai_client")
def fixture_mock_genai_client():
    """Provides a mock google.genai Client."""
    mock_client = MagicMock()
    mock_response = types.EditImageResponse()

    # Create mock generated images with base64 encoded placeholder image data
    mock_image_data = types.Image(
        gcs_uri="gs://mock_bucket/mock_image.png",
        image_bytes=b"mock_image_bytes",  # Must be bytes
        mime_type="image/png",
    )
    mock_generated_image = types.GeneratedImage(
        enhanced_prompt="Mock enhanced prompt",
        rai_filtered_reason=None,
        image=mock_image_data,
    )
    mock_response.generated_images = [
        mock_generated_image,
        mock_generated_image,
        mock_generated_image,
        mock_generated_image,
    ]

    mock_client.models.edit_image.return_value = mock_response
    return mock_client


class TestSearchController:
    """Tests for the /api/search endpoint."""

    def test_search_endpoint(self, monkeypatch, mock_genai_client):
        # Mock the ImagenSearchService to avoid actual API calls
        # Mock the google.auth.default to avoid authentication issues
        with monkeypatch.context() as m:
            mock_client_class = MagicMock(return_value=mock_genai_client)
            m.setattr("src.service.search.genai.Client", mock_client_class)
            m.setattr(
                "src.service.search.google.auth.default",
                lambda: (None, "test_project_id"),
            )
            # Mock OpenCV functions used within the service
            mock_cascade = MagicMock()
            mock_cascade.detectMultiScale.return_value = [
                (10, 10, 50, 50)
            ]  # Mock finding one face
            m.setattr(
                "src.service.search.cv2.CascadeClassifier",
                lambda x: mock_cascade,
            )
            # Mock imdecode to return a dummy numpy array with a shape
            mock_img_array = np.zeros((100, 100, 3), dtype=np.uint8)
            m.setattr(
                "src.service.search.cv2.imdecode",
                lambda buf, flags: mock_img_array,
            )
            # Mock cvtColor to return a dummy grayscale array
            mock_gray_array = np.zeros((100, 100), dtype=np.uint8)
            m.setattr(
                "src.service.search.cv2.cvtColor",
                lambda img, code: mock_gray_array,
            )

            search_term = "a cute cat wearing a hat"
            image_content = create_minimal_image_bytes()
            user_image = ("test_image.png", BytesIO(image_content), "image/png")

            response = client.post(
                "/api/search",
                data={
                    "term": search_term,
                    "numberOfImages": 4,
                    "maskDistilation": 0.005,
                    "generationModel": "imagen-3.0-capability-001",
                },
                files={"userImage": user_image},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 8

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


class TestImagenSearchService:
    """Tests for the ImagenSearchService class."""

    def test_imagen_search_service(self, monkeypatch, mock_genai_client):

        # Mock the google.auth.default to avoid authentication issues
        with monkeypatch.context() as m:
            mock_client_class = MagicMock(return_value=mock_genai_client)
            m.setattr("src.service.search.genai.Client", mock_client_class)
            m.setattr(
                "src.service.search.google.auth.default",
                lambda: (None, "test_project_id"),
            )
            # Mock OpenCV functions used within the service
            mock_cascade = MagicMock()
            mock_cascade.detectMultiScale.return_value = [
                (10, 10, 50, 50)
            ]  # Mock finding one face
            m.setattr(
                "src.service.search.cv2.CascadeClassifier",
                lambda x: mock_cascade,
            )
            # Mock imdecode to return a dummy numpy array with a shape
            mock_img_array = np.zeros((100, 100, 3), dtype=np.uint8)
            m.setattr(
                "src.service.search.cv2.imdecode",
                lambda buf, flags: mock_img_array,
            )
            # Mock cvtColor to return a dummy grayscale array
            mock_gray_array = np.zeros((100, 100), dtype=np.uint8)
            m.setattr(
                "src.service.search.cv2.cvtColor",
                lambda img, code: mock_gray_array,
            )

            valid_image_bytes = create_minimal_image_bytes()
            search_request = CreateSearchRequest(
                term="a dog playing fetch",
                user_image=valid_image_bytes,
                number_of_images=2,
                mask_distilation=0.1,
                generation_model="imagen-3.0-capability-001",
            )
            service = ImagenSearchService()
            results = service.generate_images(search_request)

        assert isinstance(results, list)
        assert len(results) == 8
        assert all(
            isinstance(result, ImageGenerationResult) for result in results
        )
        mock_client_class.assert_called_once()

        for result in results:
            assert isinstance(result.image, CustomImageResult)
            assert result.image.encoded_image == base64.b64encode(
                b"mock_image_bytes"
            ).decode("utf-8")
