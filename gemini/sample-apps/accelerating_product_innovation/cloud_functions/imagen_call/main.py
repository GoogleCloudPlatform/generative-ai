"""
Cloud function to make calls to imagen API.
"""

# pylint: disable=E0401

import os

from dotenv import load_dotenv
import functions_framework
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

load_dotenv()


PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")


def image_generation(prompt: str):
    """
    Generates images based on given prompt
    using image generation model.

    Args:
        prompt (str):
            Prompt for generating image.
    """
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    return model.generate_images(
        prompt=prompt,
        # Optional parameters
        number_of_images=1,
        language="en",
        aspect_ratio="1:1",
    )[0].__dict__["_loaded_bytes"]


@functions_framework.http
def get_images(request):
    """
    Invokes image generation call.
    Args:
        request:
            Data for image generation from the
            calling function.
    """
    request_json = request.get_json(silent=True)
    return image_generation(request_json["img_prompt"])
