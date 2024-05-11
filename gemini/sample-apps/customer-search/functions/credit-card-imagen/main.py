# pylint: disable=E0401

import json
from os import environ

import functions_framework
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

PROJECT_ID = environ.get("PROJECT_ID")
LOCATION = environ.get("LOCATION")


def get_prompt(request_json, request_args):
    """
    Gets the prompt from the request.

    Args:
        request_json (dict): The request body as a JSON object.
        request_args (dict): The request arguments as a dictionary.

    Returns:
        The prompt as a string.
    """

    if request_json and "prompt" in request_json:
        return request_json["prompt"]
    elif request_args and "prompt" in request_args:
        return request_args["prompt"]
    else:
        return "A dog reading the newspaper"


def generate_base64_image(user_prompt):
    """
    Generates a base64-encoded image using the given prompt.

    Args:
        user_prompt (str): The prompt to use for image generation.

    Returns:
        A dictionary containing the base64-encoded image.
    """

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = ImageGenerationModel.from_pretrained("imagegeneration@005")
    images = model.generate_images(prompt=user_prompt, number_of_images=1, seed=1)

    try:
        base64_image = images[0]._as_base64_string()
        return {"base64_image": base64_image}
    except Exception as e:
        print(f"Error occurred: {e}")
        return {"error": "Failed to generate or encode image."}


@functions_framework.http
def generate_credit_card_image(request):
    """
    Generates a credit card image using the given prompt.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }

        return ("", 204, headers)

    headers = {"Access-Control-Allow-Origin": "*"}

    request_json = request.get_json(silent=True)
    request_args = request.args
    prompt = get_prompt(request_json, request_args)
    base64_response = generate_base64_image(prompt)
    return (json.dumps(base64_response), 200, headers)
