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

"""Manages the lifecycle of prompts using Google Cloud Platform services.

This module provides a `gcp_prompt` class that facilitates the creation,
storage, retrieval, and execution of prompts with Vertex AI and Cloud Storage.
It handles the interaction with the Vertex AI SDK to manage prompt versions
and uses Cloud Storage to persist prompt metadata.

Key functionalities include:
- Initializing a connection to Google Cloud Platform services (Vertex AI, Cloud Storage).
- Caching and refreshing a list of existing prompts.
- Saving new or updated prompts, including their metadata, to both the
  Vertex AI prompt registry and a Cloud Storage bucket.
- Loading existing prompts from the registry and their associated metadata
  from the bucket.
- Generating responses from a specified model using a loaded prompt and
  a given set of variables.
- Helper functions for escaping special characters in prompt text.

The `model_response` Pydantic model defines the expected structure of the
response from the generative model.
"""

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.cloud import aiplatform, storage
from vertexai.generative_models import GenerationConfig
from vertexai.preview import prompts
from vertexai.preview.prompts import Prompt

load_dotenv("src/.env")

# Configure logging to the console
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

aiplatform.init(
    project=os.getenv("PROJECT_ID"),
    location=os.getenv("LOCATION"),
    staging_bucket=os.getenv("BUCKET"),
)

# --- Constants ---
PROMPT_PREFIX = os.getenv("PROMPT_PREFIX", "prompts_meta")


class GcpPrompt:
    """A wrapper class for the Vertex AI Prompt Management service."""

    def __init__(self) -> None:
        """Initializes the GcpPrompt client."""
        self.storage_client = storage.Client()

        self.refresh_prompt_cache()
        logger.info("Found %d existing prompts.", len(self.existing_prompts))

        # Load a default/initial state for the prompt metadata.
        self.prompt_meta: dict[str, Any] = {}

        self.prompt_to_run: Prompt = Prompt()
        self.refresh_bucket_cache()

    def refresh_prompt_cache(self) -> None:
        """Refreshes the local cache of existing prompts from the service."""
        self.existing_prompts = {p.display_name: p.prompt_id for p in prompts.list()}

    def refresh_bucket_cache(self) -> None:
        """Refreshes the list of metadata files from GCS."""
        blobs = self.storage_client.list_blobs(
            os.getenv("BUCKET"), prefix=PROMPT_PREFIX
        )
        self.bucket_cache_index = [i.name for i in blobs]
        logger.debug("Found %d metadata files in GCS.", len(self.bucket_cache_index))

    def _get_metadata_blob_name(self) -> str:
        """Constructs the GCS blob name for the prompt metadata file."""
        return (
            f"{PROMPT_PREFIX}/{self.prompt_to_run.prompt_name}_"
            f"{self.prompt_to_run._prompt_name}_{self.prompt_to_run._version_id}_"
            f"{self.prompt_to_run._version_name}.json"
        )

    def save_prompt(self, check_existing: bool = False) -> str:
        """Saves the current prompt.

        If check_existing is True, it ensures a prompt with the same name does not
        already exist before creating version "1".
        If check_existing is False, it creates a new version of an existing prompt.

        Args:
            check_existing: If True, raises an error if a prompt with the same
                            display name already exists.

        Returns:
            A string with the details of the saved prompt version.
        """
        logger.info("Attempting to save prompt: %s", self.prompt_to_run.prompt_name)

        if check_existing and self.prompt_to_run.prompt_name in self.existing_prompts:
            raise ValueError(
                f"Prompt with name '{self.prompt_to_run.prompt_name}' already exists. "
                "To create a new version, load the prompt and save from the "
                "'Existing Prompt' page."
            )

        if "generation_config" in self.prompt_meta and isinstance(
            self.prompt_meta["generation_config"], dict
        ):
            self.prompt_to_run.generation_config = GenerationConfig(
                **self.prompt_meta["generation_config"]
            )
        elif not isinstance(self.prompt_to_run.generation_config, GenerationConfig):
            logger.warning("No valid generation_config found. Using default.")
            self.prompt_to_run.generation_config = GenerationConfig()

        logger.debug("Prompt object being sent to SDK: %s", self.prompt_to_run)

        self.prompt_to_run = prompts.create_version(prompt=self.prompt_to_run)

        sdk_details = (
            f"SDK Prompt Version Details received:\n"
            f"- Resource Name: {self.prompt_to_run._prompt_name}\n"
            f"- Version ID: {self.prompt_to_run._version_id}\n"
            f"- Version Name: {self.prompt_to_run._version_name}\n"
            f"- Display Name: {self.prompt_to_run.prompt_name}"
        )
        logger.info(sdk_details)

        self.prompt_meta["name"] = self.prompt_to_run.prompt_name
        self.write_to_bucket()

        return sdk_details

    def load_prompt(self, prompt_id: str, prompt_name: str, version_id: str) -> None:
        """Loads a specific version of a prompt and its associated metadata."""
        self.prompt_to_run = prompts.get(prompt_id, version_id)
        self.prompt_to_run.prompt_name = prompt_name

        blob_name = self._get_metadata_blob_name()

        none_blob_name = (
            f"{PROMPT_PREFIX}/{None}_{None}_"
            f"{self.prompt_to_run._version_id}_{self.prompt_to_run._version_name}.json"
        )

        self.refresh_bucket_cache()
        bucket = self.storage_client.bucket(os.getenv("BUCKET"))

        if blob_name in self.bucket_cache_index:
            blob = bucket.blob(blob_name)
            self.prompt_meta = json.loads(blob.download_as_string())
            logger.info("Loaded metadata from %s", blob_name)
        elif none_blob_name in self.bucket_cache_index:
            logger.warning(
                "Metadata not found at %s, using fallback %s", blob_name, none_blob_name
            )
            blob = bucket.blob(none_blob_name)
            self.prompt_meta = json.loads(blob.download_as_string())

            self.write_to_bucket()
        else:
            raise FileNotFoundError(
                f"Could not find metadata file in GCS for prompt '{prompt_name}' "
                f"version '{version_id}'. Looked for '{blob_name}' and '{none_blob_name}'."
            )

    def write_to_bucket(self) -> None:
        """Writes the current prompt_meta to a GCS blob."""
        blob_name = self._get_metadata_blob_name()
        bucket = self.storage_client.bucket(os.getenv("BUCKET"))
        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            json.dumps(self.prompt_meta, indent=2), content_type="application/json"
        )
        logger.info("Wrote metadata to gs://%s/%s", os.getenv("BUCKET"), blob_name)

    def generate_response(self, variables: dict[str, Any]) -> str | None:
        """Generates a response from the currently loaded prompt and variables,
        handling image uploads.
        """
        if not self.prompt_to_run.prompt_data:
            raise ValueError("Prompt data is not loaded. Cannot generate response.")

        client = genai.Client(
            vertexai=True,
            project=os.getenv("PROJECT_ID"),
            location=os.getenv("LOCATION"),
        )
        updated_contents: list[Any] = []
        for key, value in variables.items():
            logger.info("Iterating through variables")
            if key == "image":
                if "jpg" in value or "jpeg" in value:
                    mime_type = "image/jpeg"
                elif "png" in value:
                    mime_type = "image/png"
                else:
                    logger.warning(
                        f"Unsupported image type for {value}, attempting to process as is."
                    )
                    updated_contents.append(value)
                    continue

                try:
                    # Create Image Part from URI
                    updated_contents.append(
                        genai.Part.from_uri(mime_type=mime_type, uri=value)
                    )
                except Exception as e:
                    logger.error(
                        "Error creating Part from URI for variable '%s': %s",
                        key,
                        e,
                        exc_info=True,
                    )
                    updated_contents.append(value)
            else:
                updated_contents.append(value)

        # Append the prompt text if it's not already included in variables
        prompt_text = self.prompt_to_run.prompt_data
        if not any(
            isinstance(item, str) and item == prompt_text for item in updated_contents
        ):
            updated_contents.append(prompt_text)

        logger.info("Generating response with contents: %s", updated_contents)

        model = self.prompt_to_run.model_name
        response = client.models.generate_content(
            model=model, contents=updated_contents
        )

        return response.text if response and response.text else None

    def get_generation_config_dict(self):
        """Returns the generation configuration as a dictionary."""
        return self.prompt_to_run.generation_config.to_dict()


def escape_special_characters(text: str) -> str:
    """Escapes special characters for embedding in a string.

    Note: This function is also present in gcp_dataset.py and could be moved
    to a shared utility module in the future.
    """
    if not isinstance(text, str):
        return text
    text = text.replace("\\", "\\\\")
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "\\r")
    text = text.replace("\t", "\\t")
    return text.replace('"', '\\"')
