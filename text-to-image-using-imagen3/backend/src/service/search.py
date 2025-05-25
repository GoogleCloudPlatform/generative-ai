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

import asyncio
import base64
from typing import List

import google.auth
from google import genai
from google.genai import types

from src.model.search import (
    CustomImageResult,
    ImageGenerationResult,
    SearchResponse,
)


class ImagenSearchService:
    async def _generate_with_imagen(
        self,
        client: genai.Client,
        term: str,
        generation_model: str,
        aspect_ratio: str,
        number_of_images: int,
        image_style: str,
    ) -> List[ImageGenerationResult]:
        try:
            prompt_imagen = f"Make the image with a style '{image_style}'. The user prompt is: {term}"
            print(
                f"Calling Imagen model: {generation_model} for '{term}' with style '{image_style}'"
            )

            # Run the synchronous SDK call in a separate thread
            images_imagen_response: types.GenerateImagesResponse = (
                await asyncio.to_thread(
                    client.models.generate_images,
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
                for generated_image in images_imagen_response.generated_images
            ]
            print(f"Number of images created by Imagen: {len(response_imagen)}")
            return response_imagen
        except Exception as e:
            print(f"Error during Imagen3 generation: {e}")
            return []

    async def _generate_with_gemini(
        self,
        client: genai.Client,
        term: str,
        number_of_images: int,
        image_style: str,
    ) -> List[ImageGenerationResult]:
        response_gemini: List[ImageGenerationResult] = []
        try:
            gemini_prompt_text = f"Create an image with a style '{image_style}' based on this user prompt: {term}"
            print(
                f"Calling Gemini model for '{term}' with style '{image_style}'"
            )

            for i in range(
                number_of_images
            ):  # Loop as many times as images wanted
                # Run the synchronous SDK call in a separate thread
                gemini_api_response = await asyncio.to_thread(
                    client.models.generate_content,
                    model="gemini-2.0-flash-preview-image-generation",
                    contents=gemini_prompt_text,
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"]
                    ),
                )

                for candidate in gemini_api_response.candidates:
                    for part in candidate.content.parts:
                        if (
                            part.inline_data is not None
                            and part.inline_data.mime_type.startswith("image/")
                        ):
                            encoded_image_bytes = base64.b64encode(
                                part.inline_data.data
                            ).decode("utf-8")
                            generated_text_for_prompt = ""
                            for p_text in candidate.content.parts:
                                if p_text.text is not None:
                                    generated_text_for_prompt += (
                                        p_text.text + " "
                                    )

                            finish_reason_str = (
                                candidate.finish_reason.name
                                if candidate.finish_reason
                                else None
                            )
                            if (
                                gemini_api_response.prompt_feedback
                                and gemini_api_response.prompt_feedback.blocked
                            ):
                                block_reason = (
                                    gemini_api_response.prompt_feedback.block_reason
                                )
                                block_reason_message = (
                                    gemini_api_response.prompt_feedback.block_reason_message
                                )
                                finish_reason_str = block_reason_message or (
                                    block_reason.name
                                    if block_reason
                                    else "Blocked"
                                )

                            response_gemini.append(
                                ImageGenerationResult(
                                    enhanced_prompt=generated_text_for_prompt.strip()
                                    or gemini_prompt_text,
                                    rai_filtered_reason=finish_reason_str,
                                    image=CustomImageResult(
                                        gcs_uri=None,
                                        encoded_image=encoded_image_bytes,
                                        mime_type=part.inline_data.mime_type,
                                    ),
                                )
                            )
                        elif part.text is not None:
                            print(
                                f"Gemini Text Output (not an image part): {part.text}"
                            )

            print(f"Number of images created by Gemini: {len(response_gemini)}")
            return response_gemini
        except Exception as e:
            print(f"Error during Gemini generation: {e}")
            return []

    async def generate_images(
        self,
        term: str,
        generation_model: str = "imagen-3.0-generate-002",
        aspect_ratio: str = "1:1",
        number_of_images: int = 2,
        image_style: str = "modern",
    ) -> SearchResponse:
        _, PROJECT_ID = google.auth.default()
        LOCATION = "us-central1"

        client = genai.Client(
            vertexai=True, project=PROJECT_ID, location=LOCATION
        )
        print("Async generate_images method called! Init parallel generation.")

        # Create a list of coroutines for Imagen generation
        if generation_model == "imagen-4.0-ultra-generate-exp-05-20":
            imagen_coroutines = [
                self._generate_with_imagen(
                    client=client,
                    term=term,
                    generation_model=generation_model,
                    aspect_ratio=aspect_ratio,
                    number_of_images=1,  # Imagen 4 generates 1 image per call
                    image_style=image_style,
                )
                for _ in range(number_of_images)
            ]
        else:
            imagen_coroutines = [
                self._generate_with_imagen(
                    client=client,
                    term=term,
                    generation_model=generation_model,
                    aspect_ratio=aspect_ratio,
                    number_of_images=number_of_images,
                    image_style=image_style,
                )
            ]

        gemini_coroutine = self._generate_with_gemini(
            client=client,
            term=term,
            number_of_images=number_of_images,
            image_style=image_style,
        )

        # Run tasks concurrently and gather results
        # return_exceptions=True allows us to get results even if one task fails
        all_tasks_to_gather = [*imagen_coroutines, gemini_coroutine]
        results = await asyncio.gather(
            *all_tasks_to_gather, return_exceptions=True
        )

        response_imagen: List[ImageGenerationResult] = []
        response_gemini: List[ImageGenerationResult] = []

        num_imagen_tasks = len(imagen_coroutines)

        for i in range(num_imagen_tasks):
            imagen_task_result = results[i]
            if isinstance(imagen_task_result, Exception):
                print(
                    f"Exception in Imagen generation task {i + 1}: {imagen_task_result}"
                )
            elif imagen_task_result is not None:
                response_imagen.extend(imagen_task_result)

        gemini_result_index = num_imagen_tasks
        if gemini_result_index < len(results):
            gemini_task_result = results[gemini_result_index]
            if isinstance(gemini_task_result, Exception):
                print(
                    f"Exception in Gemini generation task: {gemini_task_result}"
                )
            elif gemini_task_result is not None:
                response_gemini = gemini_task_result
        else:
            print(
                "Gemini task result not found in the expected position in results list."
            )

        return SearchResponse(
            gemini_results=response_gemini, imagen_results=response_imagen
        )
