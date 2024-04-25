"""
Cloud Function for calling Imagen API
"""

import base64
import io
import logging
import os

from dotenv import load_dotenv
import functions_framework
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

load_dotenv()


PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")


IMAGE_MODEL_NAME = "imagegeneration@005"
IMAGEN_API_ENDPOINT = f"{LOCATION}-aiplatform.googleapis.com"
IMAGEN_ENDPOINT = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{IMAGE_MODEL_NAME}"
IMAGE_UPLOAD_BYTES_LIMIT = 4096
client_options = {"api_endpoint": IMAGEN_API_ENDPOINT}
imagen_client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)


def predict_image(instance_dict: dict, parameters: dict):
    """Predicts an image using the Imagen model.

    Args:
        prompt: The text prompt to use for the image generation.
        instance_dict: A dictionary representing the instance to be predicted.
        parameters: A dictionary representing the parameters to be used for the prediction.

    Returns:
        A PIL Image object representing the generated image.
    """

    instance = json_format.ParseDict(instance_dict, Value())
    instances = [instance]
    parameters_client = json_format.ParseDict(parameters, Value())
    response = imagen_client.predict(
        endpoint=IMAGEN_ENDPOINT, instances=instances, parameters=parameters_client
    )
    response = response.predictions
    retry = 0
    while len(response) == 0 and retry < 4:
        response = imagen_client.predict(
            endpoint=IMAGEN_ENDPOINT, instances=instances, parameters=parameters_client
        )
        response = response.predictions
        retry += 1
    image_data = io.BytesIO(base64.b64decode(response[0]["bytesBase64Encoded"]))
    return image_data


def image_generation(prompt: str):
    """Generates an image using the Imagen model.

    Args:
        prompt: The text prompt to use for the image generation.

    Returns:
        A PIL Image object representing the generated image.
    """

    try:
        return predict_image(
            instance_dict={"prompt": prompt},
            parameters={"sampleCount": 1, "sampleImageSize": 256, "aspectRatio": "1:1"},
        )
    except Exception as e:
        logging.exception("An error occurred during image generation: %s", e)
        # Optionally, raise the exception here if you want to propagate it for debugging
        return (
            "An error occurred. Check server logs for details.",
            500,
        )  # More user-friendly


@functions_framework.http
def hello_http(request):
    """HTTP Cloud Function that generates an image using the Imagen model.

    Args:
        request (flask.Request): The request object.
        <http://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The generated image as a JPEG binary.
    """
    request_json = request.get_json(silent=True)
    return image_generation(request_json["img_prompt"])
