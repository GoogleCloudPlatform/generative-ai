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

import base64
from typing import List

import google.auth
from google import genai
from google.genai import types

from src.model.search import CustomImageResult, ImageGenerationResult


class ImagenSearchService:
    def generate_images(
        self,
        term: str,
        generation_model: str = "imagen-3.0-generate-002",
        aspect_ratio: str = "1:1",
        number_of_images: int = 4,
        image_style: str = "modern",
    ) -> List[ImageGenerationResult]:
        _, PROJECT_ID = google.auth.default()
        LOCATION = "northamerica-northeast1"
        client = genai.Client(
            vertexai=True, project=PROJECT_ID, location=LOCATION
        )

        prompt = f"Make the image with a style '{image_style}'. The user prompt is: {term}"
        # Imagen3 image generation
        images: types.GenerateImagesResponse = client.models.generate_images(
            model=generation_model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                enhance_prompt=True,
                safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
                person_generation="DONT_ALLOW",
            ),
        )

        # Make sure to convert the image from bytes to encoded string before sending to the frontend
        response = [
            ImageGenerationResult(
                enhanced_prompt=generated_image.enhanced_prompt,
                rai_filtered_reason=generated_image.rai_filtered_reason,
                image=CustomImageResult(
                    gcs_uri=generated_image.image.gcs_uri,
                    encoded_image=base64.b64encode(
                        generated_image.image.image_bytes
                    ).decode("utf-8"),
                    mime_type=generated_image.image.mime_type,
                ),
            )
            for generated_image in images.generated_images
        ]

        return response
