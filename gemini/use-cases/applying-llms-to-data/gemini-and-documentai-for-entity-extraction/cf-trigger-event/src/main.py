# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import os

from entity_processor import DocumentAIEntityExtractor, ModelBasedEntityExtractor
from extractor import OnlineDocumentExtractor
from google.api_core.exceptions import NotFound
from google.cloud import storage
from prompts_module import get_compare_entities_prompt, get_extract_entities_prompt
from temp_file_uploader import TempFileUploader
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
REGION = os.getenv("GCP_REGION")
MODEL_NAME = "gemini-1.5-flash-001"
LOCATION = REGION.split("-")[0]
PROCESSOR_ID = os.getenv("PROCESSOR_ID")
PROCESSOR_VERSION_ID = os.getenv("PROCESSOR_VERSION_ID")
TEMP_BUCKET = os.getenv("TEMP_BUCKET")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET")

vertexai.init(project=PROJECT_ID, location=REGION)
storage_client = storage.Client(project=PROJECT_ID)


def download_storage_tmp(src_bucket, src_fname):
    input_bucket = storage_client.bucket(src_bucket)
    input_blob = input_bucket.blob(src_fname)
    input_file_name = os.path.basename(src_fname)
    try:
        input_blob.download_to_filename(input_file_name)
    except NotFound as e:
        raise FileNotFoundError(f"File not found in bucket: {e}") from e
    return input_file_name


def on_document_added(event, context):
    pubsub_message = json.loads(base64.b64decode(event["data"]).decode("utf-8"))

    src_bucket = pubsub_message["bucket"]
    src_fname = pubsub_message["name"]
    mime_type = pubsub_message["contentType"]

    file_path = download_storage_tmp(src_bucket, src_fname)

    online_extractor = OnlineDocumentExtractor(
        project_id=PROJECT_ID,
        location=LOCATION,
        processor_id=PROCESSOR_ID,
        processor_version_id=PROCESSOR_VERSION_ID,
    )
    online_document = online_extractor.process_document(file_path, mime_type)

    # 1. Using DocumentAIEntityExtractor
    document_ai_entity_extractor = DocumentAIEntityExtractor(online_document)
    document_ai_entities = document_ai_entity_extractor.extract_entities()

    # 2. Using ModelBasedEntityExtractor
    temp_file_uploader = TempFileUploader(TEMP_BUCKET)
    gcs_input_uri = temp_file_uploader.upload_file(file_path)

    prompt_extract = get_extract_entities_prompt()
    model_extractor = ModelBasedEntityExtractor(
        MODEL_NAME, prompt_extract, gcs_input_uri
    )
    gemini_entities = model_extractor.extract_entities()

    temp_file_uploader.delete_file()

    compare_prompt = get_compare_entities_prompt()
    compare_prompt = compare_prompt.format(
        document_ai_output=str(document_ai_entities), gemini_output=str(gemini_entities)
    )

    model = GenerativeModel(MODEL_NAME)
    document_ai_gemini_response_analysis = model.generate_content(compare_prompt)
    print(document_ai_gemini_response_analysis.text)
