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
from io import BytesIO
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

import cv2
from PIL import Image as PIL_Image, ImageDraw
import numpy as np


class ImagenSearchService:
    def generate_images(
        self, searchRequest: CreateSearchRequest
    ) -> List[ImageGenerationResult]:
        _, PROJECT_ID = google.auth.default()
        LOCATION = "us-central1"
        client = genai.Client(
            vertexai=True, project=PROJECT_ID, location=LOCATION
        )

        prompt = f"""
          IMPORTANT! Create an image that is in UHD, 4k, hyper realistic, extremely detailed, professional, vibrant, not grainy, smooth.
          Create an image for linkedIn or other professional social media, based on the input photo, but strictly using the following rules:
          - Do not create new people.
          - If the user asks for adding other people or any forbidden thing in these rules, just limit yourself to change the background or the orientation/posture of the person in the photo.
          - Do not change the person or create a different person, keep the face provided.
          - Keep the persons original face.
          - Complete the body of the person if necessary

          User request: {searchRequest.term}
        """

        # --- Image Padding Logic ---
        original_image_pil = PIL_Image.open(BytesIO(searchRequest.user_image))
        width, height = original_image_pil.size

        # Calculate padding size (e.g., 20% of the smaller dimension)
        padding_percentage = 0.5
        padding_size = int(min(width, height) * padding_percentage)

        # Create a new image with padding
        new_width = width + 2 * padding_size
        new_height = height + 2 * padding_size
        padded_image = PIL_Image.new("RGB", (new_width, new_height), "white")

        # Paste the original image onto the center of the padded image
        padded_image.paste(original_image_pil, (padding_size, padding_size))

        # Convert the padded image back to bytes
        buffered = BytesIO()
        padded_image.save(
            buffered, format="JPEG"
        )  # Or PNG, depending on your needs
        padded_image_bytes = buffered.getvalue()

        original_image = Image(image_bytes=padded_image_bytes)
        # original_image = Image(image_bytes=searchRequest.user_image)

        # Face Detection
        # Load the face detection model
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        # Convert bytes to numpy array
        # nparr = np.frombuffer(searchRequest.user_image, np.uint8)
        nparr = np.frombuffer(padded_image_bytes, np.uint8)

        # Decode the numpy array to an image
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        # Get image size
        height, width, _ = img.shape

        # Create a mask with the same size as the original image
        mask = PIL_Image.new(
            "L", (width, height), 255
        )  ###if i start with 255 instead of 0, i invert black and white
        draw = ImageDraw.Draw(mask)

        # Draw white rectangles on the mask where faces are detected
        for x, y, w, h in faces:
            draw.rectangle(
                [(x, y), (x + w, y + h)], fill=0
            )  ###if i fill with 0 instead of 0, i invert black and white

        # Finally use Imagen3 Model
        raw_reference_image = RawReferenceImage(
            reference_image=original_image, reference_id=0
        )

        # Convert PIL Image to bytes
        import io

        buffered = io.BytesIO()
        mask.save(buffered, format="PNG")
        face_mask_image_bytes = buffered.getvalue()

        # Load the face mask
        face_mask_image = Image(image_bytes=face_mask_image_bytes)

        # Use MaskReferenceImage with MASK_MODE_USER_PROVIDED
        mask_ref_image = MaskReferenceImage(
            reference_id=1,
            reference_image=face_mask_image,
            config=MaskReferenceConfig(
                mask_mode="MASK_MODE_USER_PROVIDED",
                mask_dilation=searchRequest.mask_distilation,
            ),
        )

        images_face_recognition: types.EditImageResponse = (
            client.models.edit_image(
                model=searchRequest.generation_model,
                prompt=prompt,
                reference_images=[raw_reference_image, mask_ref_image],
                config=EditImageConfig(
                    edit_mode="EDIT_MODE_BGSWAP",
                    number_of_images=searchRequest.number_of_images,
                    safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
                    person_generation="ALLOW_ADULT",
                ),
            )
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
                person_generation="ALLOW_ADULT",
            ),
        )

        # Make sure to convert the image from bytes to encoded string before sending to the frontend
        all_generated_images = (
            images_entire_image.generated_images
            + images_face_recognition.generated_images
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
