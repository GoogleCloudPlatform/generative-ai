"""
Module for reading files from Google Cloud Storage.
"""

# pylint: disable=E0401

import json
import pickle
from typing import Union
from urllib.parse import urlparse

from google.cloud import storage


def read_file_from_gcs_link(gcs_link: str) -> Union[dict, bytes]:
    """Reads a JSON or pickle file directly from a Google Cloud Storage link.

    Args:
                    gcs_link (str): The gcs path to file.

    Returns:
                    data: A JSON or pkl object
    """

    storage_client = storage.Client()

    # Parse the GCS link
    parsed_url = urlparse(gcs_link)
    bucket_name = parsed_url.netloc
    blob_name = parsed_url.path.lstrip("/")  # Remove leading slash

    # Get bucket and blob references
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    file_content = blob.download_as_bytes()

    # Determine file type and decode
    if gcs_link.endswith(".json"):
        data = json.loads(file_content)
    elif gcs_link.endswith(".pkl"):
        data = pickle.loads(file_content)
    else:
        raise ValueError(
            "Unsupported file type. Please provide a JSON or pickle or jpg file."
        )

    return data
