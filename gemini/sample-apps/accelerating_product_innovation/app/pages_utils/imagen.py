"""
Utility module to:
 - Resize image bytes
 - Generate an image with Imagen
 - Edit an image with Imagen
 - Render the image generation and editing UI
"""

import io
import json
import logging
import os

from PIL import Image
import aiohttp as cloud_function_call
import streamlit as st
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

# Set project parameters
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# Set project parameters
IMAGE_MODEL_NAME = "imagegeneration@006"
model = ImageGenerationModel.from_pretrained(IMAGE_MODEL_NAME)
vertexai.init(project=PROJECT_ID, location=LOCATION)


def predict_edit_image(
    instance_dict: dict,
    parameters: dict,
) -> list[str]:
    """Predicts the output of imagen on a given instance dict.
    Args:
        instance_dict:
            The input to the large language model. (dict)
        parameters:
            The parameters for the prediction. (dict)
    Returns:
        A list of <vertexai.preview.vision_models.GeneratedImage> object
        containing the predictions.
    """

    responses = model.edit_image(
        prompt=instance_dict["prompt"],
        base_image=instance_dict["image"],
        # Optional parameters
        number_of_images=parameters["sampleCount"],
        language="en",
        mask=instance_dict["mask"],
    )
    return responses


def image_generation(
    prompt: str,
    sample_count: int,
    aspect_ratio: str,
    filename: str,
) -> None:
    """Generates an image from a prompt.

    Args:
        prompt:
            The prompt to use to generate the image.
        sample_count:
            The number of images to generate.
        aspect_ratio:
            The aspect ratio of the generated images.
        filename:
            The filename to store the image.

    Returns:
        None.
    """
    images = model.generate_images(
        prompt=prompt,
        # Optional parameters
        number_of_images=sample_count,
        language="en",
        aspect_ratio=aspect_ratio,
    )
    images[0].save(location=f"{filename}.png", include_generation_parameters=False)


async def parallel_image_generation(prompt: str, col: int):
    """
    Executes parallel generation of images through Imagen.

    Args:
        prompt (String): Prompt for image Generation.
        col (int): A pointer to the draft number of the image.
    """
    image_prompt = json.dumps({"img_prompt": prompt})
    async with cloud_function_call.ClientSession() as session:
        url = f"https://us-central1-{PROJECT_ID}.cloudfunctions.net/imagen-call"
        # Create a post request to get images.
        async with session.post(
            url,
            data=image_prompt,
            headers=st.session_state.headers,
            verify_ssl=False,
        ) as img_response:
            # Check if response is valid.
            if img_response.status == 200:
                response = await img_response.read()

                # Load response image.
                response_image = Image.open(io.BytesIO(response))
                # Save image for further use.
                response_image.save(
                    f"gen_image{st.session_state.num_drafts+col}.png", format="PNG"
                )
                return response_image
