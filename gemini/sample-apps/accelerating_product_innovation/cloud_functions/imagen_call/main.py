import logging
import os

import functions_framework
import vertexai
from dotenv import load_dotenv
from vertexai.preview.vision_models import ImageGenerationModel

load_dotenv()


PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")


def image_generation(prompt: str):
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    try:
        return model.generate_images(
            prompt=prompt,
            # Optional parameters
            number_of_images=1,
            language="en",
            aspect_ratio="1:1",
        )[0].__dict__["_loaded_bytes"]
    except Exception as e:
        logging.exception("An error occurred during image generation: %s", e)
        # Optionally, raise the exception here if you want to propagate it for debugging
        return (
            "An error occurred. Check server logs for details.",
            500,
        )  # More user-friendly


@functions_framework.http
def hello_http(request):
    request_json = request.get_json(silent=True)
    print(request_json)
    return image_generation(request_json["img_prompt"])
