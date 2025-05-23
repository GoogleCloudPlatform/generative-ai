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
from io import BytesIO

import google.auth
from google import genai
from google.genai import types
from google.genai.types import (
    RawReferenceImage,
    EditImageConfig,
    MaskReferenceImage,
    MaskReferenceConfig,
    Image as GenaiImage # Keep this alias for Imagen 3 needs this
)
from PIL import Image as PilImage # Import PIL Image and alias, Gemini uses it


from src.model.search import (
    CreateSearchRequest,
    CustomImageResult,
    ImageGenerationResult,
    SearchResponse,
)


class ImagenSearchService:
    def generate_images(
        self, searchRequest: CreateSearchRequest
    ) -> List[ImageGenerationResult]:
        _, PROJECT_ID = google.auth.default()
        LOCATION = "us-central1"
        client = genai.Client(
            vertexai=True, project=PROJECT_ID, location=LOCATION
        )

        prompt = f""" {searchRequest.term}"""

        original_image = GenaiImage(image_bytes=searchRequest.user_image)

        raw_reference_image = RawReferenceImage(
            reference_image=original_image, reference_id=0
        )

        # Imagen3 edition for just the entire image
        images_entire_image: types.EditImageResponse = client.models.edit_image(
            model=searchRequest.generation_model,
            prompt=prompt,
            reference_images=[raw_reference_image],
            config=EditImageConfig(
                edit_mode="EDIT_MODE_DEFAULT",
                number_of_images=searchRequest.number_of_images,
                safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
                person_generation="DONT_ALLOW",
            ),
        )

        # Imagen3 edition for just the background
        mask_ref_image = MaskReferenceImage(
            reference_id=1,
            reference_image=None,
            config=MaskReferenceConfig(
                mask_mode="MASK_MODE_BACKGROUND",
                segmentation_classes=[1],
                mask_dilation=searchRequest.mask_distilation,
            ),
        )
        images_just_background: types.EditImageResponse = (
            client.models.edit_image(
                model=searchRequest.generation_model,
                prompt=prompt,
                reference_images=[raw_reference_image, mask_ref_image],
                config=EditImageConfig(
                    edit_mode="EDIT_MODE_BGSWAP",
                    number_of_images=searchRequest.number_of_images,
                    safety_filter_level="BLOCK_ONLY_HIGH",
                    person_generation="DONT_ALLOW",
                ),
            )
        )

        ###Gemini response
        print(f"DEBUG: searchRequest.user_image_mime_type received: '{searchRequest.user_image_mime_type}' (Type: {type(searchRequest.user_image_mime_type)})")
        print(f"DEBUG: searchRequest.user_image length: {len(searchRequest.user_image)} bytes")

        # Convert raw image bytes to PIL Image object
        try:
            pil_image_obj = PilImage.open(BytesIO(searchRequest.user_image))
            print(f"DEBUG: Successfully created PIL Image object: {type(pil_image_obj)}")
        except Exception as e:
            print(f"ERROR: Could not open image bytes with PIL: {e}")
            raise

        gemini_model_name = "gemini-2.0-flash-preview-image-generation"
        gemini_generated_images: List[ImageGenerationResult] = []
        # Determine how many Gemini images to generate. Has to loop due to the API nature.
        num_gemini_images_to_generate = searchRequest.number_of_images #use user param

        for i in range(num_gemini_images_to_generate):
            print(f"DEBUG: Attempting to call Gemini model ({i+1}/{num_gemini_images_to_generate}): {gemini_model_name}")
            try:
                gemini_response_object: types.GenerateContentResponse = client.models.generate_content(
                    model=gemini_model_name,
                    contents=[prompt, pil_image_obj],
                    config=types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE'] #check if is faster without text
                    )
                )

                if gemini_response_object.prompt_feedback and gemini_response_object.prompt_feedback.blocked:
                    print(f"Gemini prompt blocked: {gemini_response_object.prompt_feedback.block_reason}")
                    gemini_generated_images.append(
                        ImageGenerationResult(
                            enhanced_prompt=prompt,
                            rai_filtered_reason=gemini_response_object.prompt_feedback.block_reason,
                            image=None
                        )
                    )
                    # If prompt is blocked, no point in making further calls with the same prompt
                    break
                elif gemini_response_object.candidates:
                    for candidate in gemini_response_object.candidates:
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if part.inline_data and isinstance(part.inline_data, types.Blob) and part.inline_data.mime_type.startswith("image/"):
                                    mime_type = part.inline_data.mime_type
                                    image_bytes = part.inline_data.data
                                    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
                                    enhanced_prompt = prompt
                                    if candidate.content.parts and candidate.content.parts[0].text:
                                        enhanced_prompt = candidate.content.parts[0].text

                                    gemini_generated_images.append(
                                        ImageGenerationResult(
                                            enhanced_prompt=enhanced_prompt,
                                            rai_filtered_reason=candidate.finish_reason.name if candidate.finish_reason else None,
                                            image=CustomImageResult(
                                                gcs_uri=None,
                                                mime_type=mime_type,
                                                encoded_image=encoded_image,
                                            ),
                                        )
                                    )
                                elif part.text is not None:
                                    print(f"DEBUG: Gemini Text Output for call {i+1}: {part.text}")
                        else:
                            print(f"DEBUG: Gemini response candidate {i+1} had no content parts.")
                else:
                    print(f"DEBUG: Gemini response for call {i+1} had no candidates.")

            except Exception as e:
                print(f"Error during Gemini 2.0 Flash call {i+1}: {e}")
                gemini_generated_images.append(
                    ImageGenerationResult(
                        enhanced_prompt=prompt,
                        rai_filtered_reason=f"API Error: {e}",
                        image=None
                    )
                )

        num_requested_images = searchRequest.number_of_images if searchRequest.number_of_images is not None else 4

        # Make sure to convert the image from bytes to encoded string before sending to the frontend
        response_images_entire_image = [
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
            for generated_image in images_entire_image.generated_images
        ]

        response_images_just_background = [
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
            for generated_image in images_just_background.generated_images
        ]

        response_gemini_results = gemini_generated_images[:num_requested_images] #limit to the asked number, API might duplicate.

        return SearchResponse(
            gemini_results=response_gemini_results,
            imagen_entire_img_results=response_images_entire_image,
            imagen_background_img_results=response_images_just_background,
        )
