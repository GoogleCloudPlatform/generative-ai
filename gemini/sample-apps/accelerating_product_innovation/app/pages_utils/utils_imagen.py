"""
Utility module to:
 - Resize image bytes
 - Generate an image with Imagen
 - Edit an image with Imagen
 - Render the image generation and editing UI
"""

# pylint: disable=E0401

import json
import logging
import os

import aiohttp
import cv2
import numpy as np
import streamlit as st
import vertexai
from vertexai.preview.vision_models import Image, ImageGenerationModel

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

# Set project parameters
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# Set project parameters
IMAGE_MODEL_NAME = "imagegeneration@006"
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

    model = ImageGenerationModel.from_pretrained("imagegeneration@006")

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
    model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    images = model.generate_images(
        prompt=prompt,
        # Optional parameters
        number_of_images=sample_count,
        language="en",
        aspect_ratio=aspect_ratio,
    )
    images[0].save(location=f"{filename}.png", include_generation_parameters=False)


def edit_image_generation(
    prompt: str, sample_count: int, state_key: str, mask_exists: bool
) -> bool:
    """Generates an edited image from a prompt and a base image.

    Args:
        prompt:
            A string that describes the desired edit to the image.
        sample_count:
            The number of edited images to generate.
        state_key:
            The key to store the generated images in the session state.
        mask_exists:
            Boolean value indicating if mask has been provided.

    Returns:
        Boolean value indicating if editing was completed.
    """
    input_dict = {
        "prompt": prompt,
        "image": Image.load_from_file("image_to_edit.png"),
    }

    if mask_exists:
        input_dict["mask"] = Image.load_from_file("mask.png")

    st.session_state[state_key] = predict_edit_image(
        instance_dict=input_dict,
        parameters={"sampleCount": sample_count},
    )
    return True


async def parallel_image_generation(prompt: str, col: int):
    """
    Executes parallel generation of images through Imagen.

    Args:
        prompt (String): Prompt for image Generation.
        col (int): A pointer to the draft number of the image.
    """
    data = {"img_prompt": prompt}
    data_json = json.dumps(data)
    logging.debug("Image call start")
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        url = f"https://us-central1-{PROJECT_ID}.cloudfunctions.net/imagen-call"
        # Create a post request to get images.
        async with session.post(
            url, data=data_json, headers=headers, verify_ssl=False
        ) as response:
            # Check if respose is valid.
            if response.status == 200:
                response = await response.read()
                response = cv2.imdecode(np.frombuffer(response, dtype=np.uint8), 1)
                cv2.imwrite(
                    f"gen_image{st.session_state.num_drafts+col}.png",
                    response,
                )
                return response

            print(
                "Request failed:",
                response.status,
                await response.text(),
            )
    logging.debug("Image call end")
