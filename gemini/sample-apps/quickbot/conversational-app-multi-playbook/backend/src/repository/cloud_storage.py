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

"""Provides a repository class for interacting with Google Cloud Storage (GCS).

This module defines constants related to GCS bucket structure
and includes the CloudStorageRepository class, which encapsulates operations
for interacting with GCS objects, such as listing files within a specific path.
"""

from typing import List
from google.cloud.storage import Client, Blob

BUCKET = "quick-bot"

INTENT_FOLDER = "intents"
EMBEDDINGS_FILE = "embeddings.json"
EMBEDDINGS_FOLDER = "embeddings"

CONTENT_TYPE = "text/plain"


class CloudStorageRepository:
    """A repository class for performing operations on Google Cloud Storage.

    Provides methods to interact with GCS buckets and objects, such as listing
    files within a specified path.

    Attributes:
        client: An instance of the google.cloud.storage.Client.
    """

    def __init__(self):
        """Initializes the CloudStorageRepository with a GCS client."""
        self.client = Client()

    def list(self, full_path: str) -> List[Blob]:
        """Lists all blobs (files) within a specified GCS path.

        Parses the bucket name and prefix from the full GCS path
        (e.g., "gs://your-bucket-name/path/to/files/").

        Args:
            full_path: The full GCS path (starting with "gs://") from which
                       to list blobs.

        Returns:
            A list of google.cloud.storage.blob.Blob objects found under
            the specified prefix within the bucket. Returns an empty list
            if the path is invalid or no blobs are found.

        Raises:
            ValueError: If the full_path format is invalid (e.g., doesn't
                        contain enough parts after splitting by '/').
            google.cloud.exceptions.NotFound: If the bucket does not exist.
            google.api_core.exceptions.GoogleAPICallError: For other API errors.
        """
        bucket = full_path.split("/")[2]
        prefix = full_path.replace(f"gs://{bucket}/", "")
        return list(self.client.list_blobs(bucket, prefix=prefix))
