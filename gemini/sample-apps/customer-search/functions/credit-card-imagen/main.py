import base64
import functions_framework
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import json
from os import environ

PROJECT_ID = environ.get("PROJECT_ID")
LOCATION = environ.get("LOCATION")


def get_prompt(request_json, request_args):
    if request_json and "prompt" in request_json:
        return request_json["prompt"]
    elif request_args and "prompt" in request_args:
        return request_args["prompt"]
    else:
        return "A dog reading the newspaper"


def generate_base64_image(user_prompt):
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = ImageGenerationModel.from_pretrained("imagegeneration@005")
    images = model.generate_images(
        prompt=user_prompt, number_of_images=1, seed=1
    )

    try:
        images[0].save(
            location="./gen-img1.png", include_generation_parameters=True
        )
        with open("./gen-img1.png", "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode("utf-8")
            return {"base64_image": base64_image}
    except Exception as e:
        print(f"Error occurred: {e}")
        return {"error": "Failed to generate or encode image."}


@functions_framework.http
def hello_http(request):
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
