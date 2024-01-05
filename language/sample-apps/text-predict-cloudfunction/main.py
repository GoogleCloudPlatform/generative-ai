import os
import json
import functions_framework

import google.cloud.logging

import vertexai
from vertexai.language_models import TextGenerationModel

PROJECT_ID = os.environ.get("GCP_PROJECT", "-")
LOCATION = os.environ.get("GCP_REGION", "-")

client = google.cloud.logging.Client(project=PROJECT_ID)
client.setup_logging()

log_name = "predictText-cloudfunction-log"
logger = client.logger(log_name)


@functions_framework.http
def predictText(request):
    request_json = request.get_json(silent=True)

    if request_json and "prompt" in request_json:
        prompt = request_json["prompt"]
        logger.log(f"Received request for prompt: {prompt}")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = TextGenerationModel.from_pretrained("text-bison@002")
        parameters = {
            "temperature": 0.2,
            "max_output_tokens": 256,
            "top_p": 0.8,
            "top_k": 40,
        }
        prompt_response = model.predict(prompt, **parameters)
        logger.log("PaLM Text Bison Model response: {prompt_response.text}")
    else:
        prompt_response = "No prompt provided."

    return json.dumps({"response_text": prompt_response.text})
