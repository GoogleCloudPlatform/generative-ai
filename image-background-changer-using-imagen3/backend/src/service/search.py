import base64
from typing import List

import google.auth
from google import genai
from google.genai import types
from google.genai.types import (
    Image,
    RawReferenceImage,
    EditImageConfig,
    MaskReferenceImage,
    MaskReferenceConfig,
)

from src.model.search import (
    CreateSearchRequest,
    CustomImageResult,
    ImageGenerationResult,
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

        original_image = Image(image_bytes=searchRequest.user_image)

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

        # Make sure to convert the image from bytes to encoded string before sending to the frontend
        all_generated_images = (
            images_entire_image.generated_images
            + images_just_background.generated_images
        )
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
            for generated_image in all_generated_images
        ]

        return response
