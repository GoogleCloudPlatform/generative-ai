"""
Utility module to:
 - Resize image bytes
 - Generate an image with Imagen
 - Edit an image with Imagen
 - Render the image generation and editing UI
"""

import base64
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


def predict_image(
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
        A list of strings containing the predictions.
    Raises:
        aiplatform.exceptions.NotFoundError: If the endpoint does not exist.
        aiplatform.exceptions.BadRequestError: If the input is invalid.
        aiplatform.exceptions.InternalServerError: If an internal error occurred.
    """
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    model = ImageGenerationModel.from_pretrained("imagegeneration@006")

    responses = model.edit_image(
        prompt=instance_dict["prompt"],
        base_image=instance_dict["image"],
        # Optional parameters
        number_of_images=parameters["sampleCount"],
        language="en",
        mask=instance_dict["mask"]
    )
    return responses


def image_generation(
    prompt: str,
    sample_count: int,
    sample_image_size: int,
    aspect_ratio: str,
    state_key: str,
) -> None:
    """Generates an image from a prompt.

    Args:
        prompt:
            The prompt to use to generate the image.
        sample_count:
            The number of images to generate.
        sample_image_size:
            The size of the generated images.
        aspect_ratio:
            The aspect ratio of the generated images.
        state_key:
            The key to use to store the generated images in the session state.

    Returns:
        None.
    """

    st.session_state[state_key] = predict_image(
        instance_dict={"prompt": prompt},
        parameters={
            "sampleCount": sample_count,
            "sampleImageSize": sample_image_size,
            "aspectRatio": aspect_ratio,
        },
    )


def edit_image_generation(
    prompt: str,
    sample_count: int,
    bytes_data: bytes,
    state_key: str,
    mask_bytes_data: bytes = b"",
) -> bool:
    """Generates an edited image from a prompt and a base image.

    Args:
        prompt:
            A string that describes the desired edit to the image.
        sample_count:
            The number of edited images to generate.
        bytes_data:
            The image data in bytes.
        state_key:
            The key to store the generated images in the session state.
        mask_bytes_data:
            The mask data in bytes.

    Returns:
        Boolean value indicating if editing was completed.
    """
    input_dict = {
        "prompt": prompt,
        "image": Image.load_from_file("image_to_edit.png"),
    }

    if mask_bytes_data:
        input_dict["mask"] = Image.load_from_file("mask.png")

    st.session_state[state_key] = predict_image(
        instance_dict=input_dict,
        parameters={"sampleCount": sample_count},
    )
    return True


async def parallel_image_generation(prompt: str, col: int) -> None:
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
        async with session.post(
            url, data=data_json, headers=headers, verify_ssl=False
        ) as response:
            logging.debug("Inside IF else of session")
            if response.status == 200:
                response = await response.read()
                response = cv2.imdecode(np.frombuffer(response, dtype=np.uint8), 1)
                cv2.imwrite(
                    f"gen_image{st.session_state.num_drafts+col}.png",
                    response,
                )
                return response
            else:
                print(
                    "Request failed:",
                    response.status,
                    await response.text(),
                )
    logging.debug("Image call end")
