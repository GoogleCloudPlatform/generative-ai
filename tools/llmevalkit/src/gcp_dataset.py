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


"""This module provides utility functions for managing and processing datasets
stored on Google Cloud Storage (GCS).

It includes functionalities to:
- List available datasets from a specified GCS bucket.
- Fetch and read CSV files from GCS into pandas DataFrames.
- Process raw data from CSVs to generate structured user prompts and expected
  outcomes for model evaluation.
- A helper function to escape special characters in text to be used with the
  Gemini API.

The primary purpose is to abstract the GCS interactions and data preprocessing
steps required for the prompt management and evaluation application.
"""

import io
import logging
import os

import pandas as pd
from dotenv import load_dotenv
from google.cloud import storage

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv("src/.env")


PREFIX = "datasets_meta"


def get_existing_datasets() -> list[str]:
    """Gets the list of existing dataset names from the GCS bucket.

    Returns:
        list[str]: A list of dataset names.
    """
    storage_client = storage.Client()
    blobs = storage_client.list_blobs(os.getenv("BUCKET_NAME"), prefix=PREFIX)
    return [i.name.split("/")[-1] for i in blobs]


def escape_special_characters(text: str) -> str:
    """Escapes special characters for Gemini Flash API."""
    if not isinstance(text, str):
        return text
    text = text.replace("\\", "\\")
    text = text.replace("\n", "\n")
    text = text.replace("\r", "\r")
    text = text.replace("\t", "\t")
    return text.replace('"', '"')


def process_csv_from_gcs(bucket_name: str, file_path: str) -> pd.DataFrame:
    """Reads a CSV file from GCS, processes each row to create user prompts
    and expected results, and returns a pandas DataFrame.

    Args:
        bucket_name: Name of the GCS bucket.
        file_path: Path to the CSV file within the bucket.

    Returns:
        pandas.DataFrame: DataFrame with original data and added user_prompt
                          and expected_result columns.
    """
    try:
        client = storage.Client()
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(file_path)

        content = blob.download_as_bytes()

        return pd.read_csv(io.BytesIO(content))

    except (OSError, ValueError) as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame()
