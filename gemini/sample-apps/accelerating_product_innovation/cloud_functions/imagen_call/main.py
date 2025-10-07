"""
Cloud function to make calls to Imagen API.
"""

import os
from typing import Any

from dotenv import load_dotenv
import functions_framework
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")


def image_generation(prompt: str) -> bytes:
    """Generates images based on given prompt using image generation model.

    Args:
        prompt (str): Prompt for generating image.

    Returns:
        bytes: The generated image as raw bytes.
    """
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    image = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        language="en",
        aspect_ratio="1:1",
    )[0]
    return image._loaded_bytes  # pylint: disable=protected-access


@functions_framework.http
def get_images(request: Any) -> bytes:
    """Invokes image generation call.

    Args:
        request: Data for image generation from the calling function.

    Returns:
        Response: A Flask Response object containing the generated image.
    """
    request_json: dict = request.get_json(silent=True)
    return image_generation(request_json["img_prompt"])
