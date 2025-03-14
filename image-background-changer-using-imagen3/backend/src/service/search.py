import base64
from typing import List

import google.auth
from google import genai
from google.genai import types
from google.genai.types import Image, RawReferenceImage, EditImageConfig, MaskReferenceImage, MaskReferenceConfig

from src.model.search import CustomImageResult, ImageGenerationResult

test_image = "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
test_image_bytes = base64.b64decode(test_image) # Decode the base64 string

class ImagenSearchService:
    def generate_images(
        self,
        user_image: bytes,
        term: str,
        generation_model: str = "imagen-3.0-capability-001",
        aspect_ratio: str = "1:1",
        number_of_images: int = 4,
        image_style: str = "modern",
    ) -> List[ImageGenerationResult]:
        _, PROJECT_ID = google.auth.default()
        LOCATION = "northamerica-northeast1"
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

        prompt = f"Change the background of the image, try a plain color, like black, white, blue or orange. Make it '{image_style}'. The user prompt is: {term}"

        image_object = Image(image_bytes=test_image_bytes) #test_image or user_image bytes

        raw_reference_image = RawReferenceImage(reference_image=image_object, reference_id=0)

        mask_ref_image = MaskReferenceImage(
            reference_id=1,
            reference_image=None,
            config=MaskReferenceConfig(
                mask_mode="MASK_MODE_BACKGROUND",
                segmentation_classes=[2],
                mask_dilation=0.01,
            ),
        )
        
        # Imagen3 image edition
        images: types.EditImageResponse = client.models.edit_image(
            model=generation_model,
            prompt=prompt,
            reference_images=[raw_reference_image, mask_ref_image],
            config=EditImageConfig(
                edit_mode="EDIT_MODE_BGSWAP", #EDIT_MODE_BGSWAP, EDIT_MODE_INPAINT_INSERTION, EDIT_MODE_INPAINT_INSERTION
                number_of_images=1,
                safety_filter_level="BLOCK_ONLY_HIGH", #BLOCK_MEDIUM_AND_ABOVE,
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
