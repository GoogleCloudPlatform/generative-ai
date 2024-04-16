"""
Utility module to:
 - Resize image bytes
 - Generate an image with Imagen
 - Edit an image with Imagen
 - Render the image generation and editing UI
"""

import base64
import json
import os
import logging
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
import streamlit as st
import cv2
import numpy as np
import aiohttp

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

# Set project parameters
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# Set project parameters
IMAGE_MODEL_NAME = "imagegeneration@005"
IMAGE_MODEL_NAME_ = "imagegeneration@002"
IMAGEN_API_ENDPOINT = f"{LOCATION}-aiplatform.googleapis.com"
IMAGEN_ENDPOINT = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{IMAGE_MODEL_NAME}"
IMAGEN_ENDPOINT_ = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{IMAGE_MODEL_NAME_}"
IMAGE_UPLOAD_BYTES_LIMIT = 4096
# The AI Platform services require regional API endpoints.
client_options = {"api_endpoint": IMAGEN_API_ENDPOINT}
# Initialize client that will be used to create and send requests.
imagen_client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)


def predict_image(
    instance_dict: dict, parameters: dict, endpoint_name: str = IMAGEN_ENDPOINT
):
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

    instance = json_format.ParseDict(instance_dict, Value())
    instances = [instance]
    parameters_client = json_format.ParseDict(parameters, Value())
    response = imagen_client.predict(
        endpoint=endpoint_name, instances=instances, parameters=parameters_client
    )
    return response.predictions


def image_generation(
    prompt: str,
    sample_count: int,
    sample_image_size: int,
    aspect_ratio: str,
    state_key: str,
):
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
):
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
        None.
    """
    input_dict = {
        "prompt": prompt,
        "image": {"bytesBase64Encoded": base64.b64encode(bytes_data).decode("utf-8")},
    }

    if mask_bytes_data:
        input_dict["mask"] = {
            "image": {
                "bytesBase64Encoded": base64.b64encode(mask_bytes_data).decode("utf-8")
            }
        }

    st.session_state[state_key] = predict_image(
        instance_dict=input_dict,
        parameters={"sampleCount": sample_count},
        endpoint_name=IMAGEN_ENDPOINT_,
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
    data = json.dumps(data)
    logging.debug("Image call start")
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        url = f"https://us-central1-{PROJECT_ID}.cloudfunctions.net/imagen-call"
        async with session.post(
            url, data=data, headers=headers, verify_ssl=False
        ) as response:
            logging.debug("Inside IF else of session")
            if response.status == 200:
                response = await response.read()
                response = cv2.imdecode(np.frombuffer(response, dtype=np.uint8), 1)
                cv2.imwrite(f"gen_image{st.session_state.num_drafts+col}.png", response)
                return response
            else:
                print("Request failed:", response.status, await response.text())
    logging.debug("Image call end")
