import base64

import google.auth
from google import genai
from google.genai import types

from src.model.search import CustomImageResult, ImageGenerationResult


class ImagenSearchService:
    def generate_images(self, term: str):
        _, PROJECT_ID = google.auth.default()
        LOCATION = "northamerica-northeast1"
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

        generation_model = "imagen-3.0-generate-002"
        # Imagen 3 image generation
        images: types.GenerateImagesResponse = client.models.generate_images(
            model=generation_model,
            prompt=term,
            config=types.GenerateImagesConfig(
                number_of_images=4,
                aspect_ratio="1:1",
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
