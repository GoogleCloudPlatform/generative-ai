import os
import json
import functions_framework

import google.cloud.logging

import vertexai
from vertexai.preview.language_models import CodeGenerationModel

PROJECT_ID = os.environ.get("GCP_PROJECT", "-")
LOCATION = os.environ.get("GCP_REGION", "-")

client = google.cloud.logging.Client(project=PROJECT_ID)
client.setup_logging()

LOG_NAME = "predictCode-cloudfunction-log"
logger = client.logger(LOG_NAME)


@functions_framework.http
def predictCode(request):
    request_json = request.get_json(silent=True)

    if request_json and "prompt" in request_json:
        prompt = request_json["prompt"]
        logger.log(f"Received request for prompt: {prompt}")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        parameters = {"temperature": 0.2, "max_output_tokens": 1024}
        model = CodeGenerationModel.from_pretrained("code-bison@002")
        prompt_response = model.predict(prompt, **parameters)
        logger.log(f"PaLM Code Bison Model response: {prompt_response.text}")
    else:
        prompt_response = "No prompt provided."

    return json.dumps({"response_text": prompt_response.text})
