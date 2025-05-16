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
        LOCATION = "us-central1"
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        print("generate_images method called!")
        
        response_imagen: List[ImageGenerationResult] = []
        response_gemini: List[ImageGenerationResult] = []

            # --- Imagen3 Image Generation ---
        try:
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

            prompt = f"Make the image with a style '{image_style}'. The user prompt is: {term}"
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
            print(f"Number of images created by Imagen: {len(response_imagen)}")

        except Exception as e:
            print(f"Error during Imagen3 generation: {e}")

            # --- Gemini Image Generation ---
        try:
            print("Initializing Gemini client")
            gemini_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

            gemini_prompt_text = f"Create a 3d rendered image with a style '{image_style}' based on this user prompt: {term}"
            
            for _ in range(number_of_images):  # Loop as many times as images wanted
                print(f"Calling Gemini model: gemini-2.0-flash-preview-image-generation with prompt: '{gemini_prompt_text}'")
                gemini_api_response = gemini_client.models.generate_content(
                    model="gemini-2.0-flash-preview-image-generation",
                    contents=gemini_prompt_text,
                    config=types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']
                    )
                )

                # Process gemini_api_response as per the documentation and your needs
                for candidate in gemini_api_response.candidates: # Iterate through candidates
                    for part in candidate.content.parts:
                        if part.inline_data is not None and part.inline_data.mime_type.startswith("image/"):
                            encoded_image_bytes = base64.b64encode(part.inline_data.data).decode("utf-8")
                            # Determine enhanced_prompt and rai_filtered_reason from the response if available
                            generated_text_for_prompt = ""
                            for p_text in candidate.content.parts: # check for text part in the same candidate
                                if p_text.text is not None:
                                    generated_text_for_prompt += p_text.text + " "
                            
                            finish_reason_str = candidate.finish_reason.name if candidate.finish_reason else None
                            if gemini_api_response.prompt_feedback and gemini_api_response.prompt_feedback.blocked:
                                finish_reason_str = gemini_api_response.prompt_feedback.block_reason_message or gemini_api_response.prompt_feedback.block_reason.name


                            response_gemini.append(
                                ImageGenerationResult(
                                    enhanced_prompt=generated_text_for_prompt.strip() or gemini_prompt_text, 
                                    rai_filtered_reason=finish_reason_str,
                                    image=CustomImageResult(
                                        gcs_uri=None,
                                        encoded_image=encoded_image_bytes,
                                        mime_type=part.inline_data.mime_type,
                                    ),
                                )
                            )
                        elif part.text is not None:
                            print(f"Gemini Text Output: {part.text}")


            print(f"Number of images created by Gemini: {len(response_gemini)}")
            # Combine response_gemini with response_imagen
            combined_response = response_imagen + response_gemini[:number_of_images]
            return combined_response

        except Exception as e:
            print(f"111 Error during Image generation: {e}")
            return []