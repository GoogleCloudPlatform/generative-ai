import base64
from typing import List
from io import BytesIO

import google.auth
from google import genai
from google.genai import types
from PIL import Image

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
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        print("generate_images method called!") # <--- Add this

        # --- Imagen3 Image Generation ---
        prompt_imagen = f"Make the image with a style '{image_style}'. The user prompt is: {term}"
        images_imagen: types.GenerateImagesResponse = client.models.generate_images(
            model=generation_model,
            prompt=prompt_imagen,
            config=types.GenerateImagesConfig(
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                enhance_prompt=True,
                safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
                person_generation="DONT_ALLOW",
            ),
        )

        response_imagen = [
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
            for generated_image in images_imagen.generated_images
        ]

        # Debugging: Print the number of images created by Imagen
        print(f"Number of images created by Imagen: {len(response_imagen)}")

        # --- Gemini Image Generation ---
        # Initialize a separate client for Gemini if needed, though genai.Client() can often handle both.
        # For simplicity, we'll reuse the existing client if possible, or create a new one if it causes issues.
        # client_gemini = genai.Client() # Uncomment if you need a separate client for Gemini
        
        response_gemini: List[ImageGenerationResult] = []
        gemini_prompt = f"Create a 3d rendered image with a style '{image_style}' based on this user prompt: {term}"

        for _ in range(number_of_images):  # Loop as many times as images wanted
            gemini_response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=gemini_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )

            for part in gemini_response.candidates[0].content.parts:
                if part.inline_data is not None:
                    # Gemini returns the image bytes directly
                    encoded_image_bytes = base64.b64encode(part.inline_data.data).decode("utf-8")
                    response_gemini.append(
                        ImageGenerationResult(
                            enhanced_prompt=gemini_prompt,
                            rai_filtered_reason=None,
                            image=CustomImageResult(
                                gcs_uri=None,
                                encoded_image=encoded_image_bytes,
                                mime_type=part.inline_data.mime_type,
                            ),
                        )
                    )

        # Debugging: Print the number of images created by Gemini
        print(f"Number of images created by Gemini: {len(response_gemini)}")

        # Combine results from both Imagen and Gemini
        combined_response = response_imagen + response_gemini

        return combined_response