import os
import functions_framework
from google.cloud import storage

import vertexai
from vertexai.language_models import TextGenerationModel
import google.cloud.logging


PROJECT_ID = os.environ.get("GCP_PROJECT", "-")
LOCATION = os.environ.get("GCP_REGION", "-")

client = google.cloud.logging.Client(project=PROJECT_ID)
client.setup_logging()

LOG_NAME = "summarize-cloudfunction-log"
logger = client.logger(LOG_NAME)


def predict_text(prompt, **parameters):
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = TextGenerationModel.from_pretrained("text-bison@002")
    prompt_response = model.predict(prompt, **parameters)
    return prompt_response.text


@functions_framework.cloud_event
def summarize_gcs_object(cloud_event):
    data = cloud_event.data

    bucketname = data["bucket"]
    name = data["name"]

    # Read the contents of the blob
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucketname)
    blob = bucket.blob(name)

    file_contents = blob.download_as_text(encoding="utf-8")

    # Invoke the predict function with the Summarize prompt
    prompt = f"Summarize the following: {file_contents}"
    parameters = {
        "temperature": 0.2,
        "max_output_tokens": 256,
        "top_p": 0.8,
        "top_k": 40,
    }
    prompt_response = predict_text(prompt, **parameters)

    # Save the summary in another blob (same name as the original blob) in the summary bucket
    summary_blob_name = name
    summarization_bucket = storage_client.bucket(f"{bucketname}-summaries")
    summary_blob = summarization_bucket.blob(summary_blob_name)
    summary_blob.upload_from_string(prompt_response.encode("utf-8"))
    logger.log(f"Summarization saved in {summary_blob_name} in {bucketname}-summaries.")
