# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Main logic for classification and entity extraction."""

import json
import os

import dotenv
import utils
from google import genai
from google.genai import types

EXTRACT_PROMPT_TEMPLATE = """\
    Based solely on this {document_name}, extract the following fields.
    If the information is missing, write "missing" next to the field.
    Output as JSON.

    Fields:\n
    {fields}
"""

CLASSIFY_PROMPT_TEMPLATE = """\
    Based on the content of the document, classify it as one of the following classes.
    Output as JSON in the following format:
    "class": "class_name"


    Classes:\n
    {classes}
"""

dotenv.load_dotenv()
project_id = os.environ.get("GEMINI_PROJECT_ID")
if not project_id:
    raise ValueError("GEMINI_PROJECT_ID environment variable must be set.")
location = os.environ.get("GEMINI_LOCATION", "global")
config_path = os.environ.get("CONFIG_PATH", "config.json")

# Initialize Gemini client.
client = genai.Client(vertexai=True, project=project_id, location=location)
CONFIGS = utils.load_app_config(config_path)


def extract_from_document(extract_config_id: str, document_uri: str) -> str:
    """Extract entities from a document."""
    extract_config = CONFIGS["extraction_configs"][extract_config_id]

    prompt = EXTRACT_PROMPT_TEMPLATE.format(
        document_name=extract_config["document_name"],
        fields=json.dumps(extract_config["fields"], indent=4),
    )

    response = client.models.generate_content(
        model=extract_config["model"],
        contents=[
            types.Part.from_uri(
                file_uri=document_uri,
                mime_type=extract_config["document_mime_type"],
            ),
            prompt,
        ],
        config={
            "response_mime_type": "application/json",
        },
    )
    return response.text


def classify_document(document_uri: str) -> str:
    """Classify a document."""
    classification_config = CONFIGS["classification_config"]

    prompt = CLASSIFY_PROMPT_TEMPLATE.format(
        classes=json.dumps(classification_config["classes"], indent=4),
    )

    response = client.models.generate_content(
        model=classification_config["model"],
        contents=[
            types.Part.from_uri(
                file_uri=document_uri,
                mime_type=classification_config["document_mime_type"],
            ),
            prompt,
        ],
        config={
            "response_mime_type": "application/json",
        },
    )
    return response.text


def classify_and_extract_document(document_uri: str) -> str:
    """Classify a document and extract entities from it."""
    classification_response = classify_document(document_uri)
    classification_result = json.loads(classification_response)
    document_class = classification_result.get("class")
    if not document_class or document_class not in CONFIGS["extraction_configs"]:
        raise ValueError("Document classification failed.")

    return extract_from_document(document_class, document_uri)
