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

"""Utilities for entity extraction."""

import json
import logging

from google.cloud import storage


def load_config_from_gcs(bucket_name: str, file_name: str) -> dict:
    """Downloads a file from GCS and parses it as JSON."""
    logging.info(f"Loading config from GCS: gs://{bucket_name}/{file_name}")
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        config_data = blob.download_as_string()
        return json.loads(config_data)
    except Exception as e:
        logging.info(f"ERROR: Failed to load GCS config: {e}")
        raise


def load_config_from_local(file_path: str) -> dict:
    """Loads a config file from the local filesystem."""
    logging.info(f"Loading config from local file: {file_path}")
    try:
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        logging.info(f"ERROR: Failed to load local config {file_path}: {e}")
        raise


def load_app_config(config_path: str) -> dict:
    """Loads entity extraction configurations from GCS or local based on path prefix."""
    if config_path.startswith("gs://"):
        try:
            # Parse the GCS path: "gs://[BUCKET_NAME]/[FILE_PATH]"
            path_parts = config_path.replace("gs://", "").split("/", 1)
            bucket_name = path_parts[0]
            file_path = path_parts[1]
            return load_config_from_gcs(bucket_name, file_path)
        except Exception as e:
            logging.info(f"ERROR: Could not parse GCS path '{config_path}': {e}")
            raise
    else:
        # Treat it as a local file path
        return load_config_from_local(config_path)
