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

import asyncio  # Added for parallel execution
import base64
from typing import List, Optional
from io import BytesIO

import google.auth
from google import genai
from google.genai import types
from google.genai.types import (
    RawReferenceImage,
    EditImageConfig,
    MaskReferenceImage,
    MaskReferenceConfig,
    Image as GenaiImage,  # Keep this alias for Imagen 3 needs this
    Blob as GenaiBlob,  # Added for type checking in Gemini response
)
from PIL import Image as PilImage  # Import PIL Image and alias, Gemini uses it


from src.model.search import (
    CreateSearchRequest,
    CustomImageResult,
    ImageGenerationResult,
    SearchResponse,
)


class ImagenSearchService:
    # Helper function for Imagen3 edit_image (entire image)
    @staticmethod
    async def _generate_imagen_entire_image_task(
        client: genai.Client,
        model_name: str,  # Changed from 'model' to 'model_name' for clarity
        prompt: str,
        raw_reference_image: RawReferenceImage,
        number_of_images: int,
    ) -> types.EditImageResponse:
        def blocking_call() -> types.EditImageResponse:
            return client.models.edit_image(
                model=model_name,
                prompt=prompt,
                reference_images=[raw_reference_image],
                config=EditImageConfig(
                    edit_mode="EDIT_MODE_DEFAULT",
                    number_of_images=number_of_images,
                    safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
                    person_generation="DONT_ALLOW",
                ),
            )

        return await asyncio.to_thread(blocking_call)

    # Helper function for Imagen3 edit_image (background swap)
    @staticmethod
    async def _generate_imagen_background_task(
        client: genai.Client,
        model_name: str,  # Changed from 'model' to 'model_name' for clarity
        prompt: str,
        raw_reference_image: RawReferenceImage,
        mask_ref_image: MaskReferenceImage,
        number_of_images: int,
    ) -> types.EditImageResponse:
        def blocking_call() -> types.EditImageResponse:
            return client.models.edit_image(
                model=model_name,
                prompt=prompt,
                reference_images=[raw_reference_image, mask_ref_image],
                config=EditImageConfig(
                    edit_mode="EDIT_MODE_BGSWAP",
                    number_of_images=number_of_images,
                    safety_filter_level="BLOCK_ONLY_HIGH",
                    person_generation="DONT_ALLOW",
                ),
            )

        return await asyncio.to_thread(blocking_call)

    @staticmethod
    async def _generate_single_gemini_image_task(
        client: genai.Client,
        gemini_model_name: str,
        prompt: str,
        user_image_bytes: bytes,  # Changed to accept bytes
    ) -> ImageGenerationResult:
        try:
            # Create PIL Image object inside the task
            pil_image_obj = PilImage.open(BytesIO(user_image_bytes))
        except Exception as e:
            print(f"Error opening image for Gemini task: {e}")
            return ImageGenerationResult(
                enhanced_prompt=prompt,
                rai_filtered_reason=f"Image Processing Error: {str(e)}",
                image=None,
            )

        def blocking_call() -> types.GenerateContentResponse:
            return client.models.generate_content(
                model=gemini_model_name,
                contents=[prompt, pil_image_obj],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                ),
            )

        try:
            gemini_response_object = await asyncio.to_thread(blocking_call)

            if (
                gemini_response_object.prompt_feedback
                and gemini_response_object.prompt_feedback.blocked
            ):
                print(
                    f"Gemini prompt blocked: {gemini_response_object.prompt_feedback.block_reason}"
                )
                return ImageGenerationResult(
                    enhanced_prompt=prompt,
                    rai_filtered_reason=str(
                        gemini_response_object.prompt_feedback.block_reason.name
                    ),
                    image=None,
                )

            if not gemini_response_object.candidates:
                print("DEBUG: Gemini response had no candidates.")
                return ImageGenerationResult(
                    enhanced_prompt=prompt,
                    rai_filtered_reason="No candidates in response",
                    image=None,
                )

            for candidate in gemini_response_object.candidates:
                if not (candidate.content and candidate.content.parts):
                    print(
                        "DEBUG: Gemini response candidate had no content parts."
                    )
                    continue

                image_part_data: Optional[GenaiBlob] = None
                enhanced_prompt_text = prompt

                text_parts = [
                    p.text
                    for p in candidate.content.parts
                    if p.text is not None
                ]
                if text_parts:
                    enhanced_prompt_text = text_parts[0]

                for part in candidate.content.parts:
                    if (
                        part.inline_data
                        and isinstance(part.inline_data, GenaiBlob)
                        and part.inline_data.mime_type.startswith("image/")
                    ):
                        image_part_data = part.inline_data
                        break

                if image_part_data:
                    mime_type = image_part_data.mime_type
                    image_bytes_data = image_part_data.data
                    encoded_image = base64.b64encode(image_bytes_data).decode(
                        "utf-8"
                    )

                    return ImageGenerationResult(
                        enhanced_prompt=enhanced_prompt_text,
                        rai_filtered_reason=(
                            str(candidate.finish_reason.name)
                            if candidate.finish_reason
                            else None
                        ),
                        image=CustomImageResult(
                            gcs_uri=None,
                            mime_type=mime_type,
                            encoded_image=encoded_image,
                        ),
                    )
                else:
                    print(
                        f"DEBUG: Gemini candidate did not yield a usable image. Finish reason: {candidate.finish_reason}"
                    )

            return ImageGenerationResult(
                enhanced_prompt=prompt,
                rai_filtered_reason="No image data in response candidates",
                image=None,
            )

        except Exception as e:
            # Catch specific exceptions from the SDK if possible, or broader ones
            print(
                f"Error during Gemini API call for prompt '{prompt[:50]}...': {e}"
            )
            return ImageGenerationResult(
                enhanced_prompt=prompt,
                rai_filtered_reason=f"API Error: {str(e)}",
                image=None,
            )

    async def generate_images(
        self, searchRequest: CreateSearchRequest
    ) -> SearchResponse:
        _, PROJECT_ID = google.auth.default()
        LOCATION = "us-central1"
        client = genai.Client(
            vertexai=True, project=PROJECT_ID, location=LOCATION
        )

        prompt = f"""{searchRequest.term}"""

        # Validate user_image bytes early, but PIL object creation will be per-task for Gemini
        try:
            # Quick check if image is somewhat valid, without keeping it open
            PilImage.open(BytesIO(searchRequest.user_image)).close()
        except Exception as e:
            print(f"ERROR: User image bytes are invalid: {e}")
            raise ValueError(f"Invalid user image file: {e}")

        original_image_genai = GenaiImage(image_bytes=searchRequest.user_image)
        # Use string IDs for reference_id as expected by the API
        raw_reference_image = RawReferenceImage(
            reference_image=original_image_genai,
            reference_id=0,
        )

        mask_ref_image_for_bg_swap = MaskReferenceImage(
            reference_id=1,
            reference_image=None,
            config=MaskReferenceConfig(
                mask_mode="MASK_MODE_BACKGROUND",
                segmentation_classes=[1],
                mask_dilation=searchRequest.mask_distilation,
            ),
        )

        imagen_model_to_use = searchRequest.generation_model
        num_images_to_generate = searchRequest.number_of_images

        imagen_entire_task = self._generate_imagen_entire_image_task(
            client,
            imagen_model_to_use,
            prompt,
            raw_reference_image,
            num_images_to_generate,
        )

        imagen_background_task = self._generate_imagen_background_task(
            client,
            imagen_model_to_use,
            prompt,
            raw_reference_image,
            mask_ref_image_for_bg_swap,
            num_images_to_generate,
        )

        gemini_model_name = "gemini-2.0-flash-preview-image-generation"
        gemini_tasks = [
            self._generate_single_gemini_image_task(
                client, gemini_model_name, prompt, searchRequest.user_image
            )
            for _ in range(num_images_to_generate)
        ]

        async def gather_gemini_results_async():
            results = await asyncio.gather(
                *gemini_tasks, return_exceptions=True
            )
            processed_results = []
            for i, res in enumerate(results):
                if isinstance(res, ImageGenerationResult):
                    processed_results.append(res)
                elif isinstance(res, Exception):
                    print(f"Gemini task {i+1} failed: {res}")
                    processed_results.append(
                        ImageGenerationResult(
                            enhanced_prompt=prompt,
                            rai_filtered_reason=f"Gemini Task Error: {str(res)}",
                            image=None,
                        )
                    )
                else:
                    print(
                        f"Gemini task {i+1} returned unexpected type: {type(res)}"
                    )
                    processed_results.append(
                        ImageGenerationResult(
                            enhanced_prompt=prompt,
                            rai_filtered_reason="Gemini Task Internal Error: Unexpected Result Type",
                            image=None,
                        )
                    )
            return processed_results

        all_task_results = await asyncio.gather(
            imagen_entire_task,
            imagen_background_task,
            gather_gemini_results_async(),
            return_exceptions=True,
        )

        response_images_entire_image: List[ImageGenerationResult] = []
        if isinstance(all_task_results[0], types.EditImageResponse):
            images_entire_raw = all_task_results[0]
            if images_entire_raw.generated_images:
                response_images_entire_image = [
                    ImageGenerationResult(
                        enhanced_prompt=img.enhanced_prompt,
                        rai_filtered_reason=img.rai_filtered_reason,
                        image=CustomImageResult(
                            gcs_uri=img.image.gcs_uri,
                            encoded_image=base64.b64encode(
                                img.image.image_bytes
                            ).decode("utf-8"),
                            mime_type=img.image.mime_type,
                        ),
                    )
                    for img in images_entire_raw.generated_images
                ]
        elif isinstance(all_task_results[0], Exception):
            print(
                f"Imagen entire image generation failed: {all_task_results[0]}"
            )

        response_images_just_background: List[ImageGenerationResult] = []
        if isinstance(all_task_results[1], types.EditImageResponse):
            images_background_raw = all_task_results[1]
            if images_background_raw.generated_images:
                response_images_just_background = [
                    ImageGenerationResult(
                        enhanced_prompt=img.enhanced_prompt,
                        rai_filtered_reason=img.rai_filtered_reason,
                        image=CustomImageResult(
                            gcs_uri=img.image.gcs_uri,
                            encoded_image=base64.b64encode(
                                img.image.image_bytes
                            ).decode("utf-8"),
                            mime_type=img.image.mime_type,
                        ),
                    )
                    for img in images_background_raw.generated_images
                ]
        elif isinstance(all_task_results[1], Exception):
            print(
                f"Imagen background swap generation failed: {all_task_results[1]}"
            )

        gemini_generated_results_list: List[ImageGenerationResult] = []
        if isinstance(all_task_results[2], list):
            gemini_generated_results_list = all_task_results[2]
        elif isinstance(all_task_results[2], Exception):
            print(
                f"Gathering Gemini results task itself failed: {all_task_results[2]}"
            )

        valid_gemini_results = [
            res
            for res in gemini_generated_results_list
            if res.image is not None
        ]
        response_gemini_results = valid_gemini_results[:num_images_to_generate]

        return SearchResponse(
            gemini_results=response_gemini_results,
            imagen_entire_img_results=response_images_entire_image,
            imagen_background_img_results=response_images_just_background,
        )
