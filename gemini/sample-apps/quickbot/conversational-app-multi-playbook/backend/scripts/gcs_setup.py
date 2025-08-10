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

"""Utility functions for setting up Google Cloud Storage (GCS) buckets.

This module provides functions to interact with GCS, specifically for
creating buckets needed by the application. It also defines constants
for bucket configuration like name pattern, content type, and location.
"""

from google.cloud.storage import Client as GCSClient
from scripts.big_query_setup import PROJECT_ID

BUCKET = f"quick-bot-{PROJECT_ID}"
CONTENT_TYPE = "text/plain"
LOCATION = "us-central1"

storage_client = GCSClient()


def create_bucket(bucket_name: str):
    """Creates a Google Cloud Storage bucket if it doesn't already exist.

    Checks if a bucket with the specified name exists. If not, it creates
    a new bucket in the predefined LOCATION.

    Args:
        bucket_name: The desired name for the GCS bucket.

    Returns:
        A google.cloud.storage.bucket.Bucket object representing the
        existing or newly created bucket.
    """
    storage_bucket = storage_client.bucket(bucket_name)
    if not storage_bucket.exists():
        print(f"{bucket_name} Bucket does not exist, creating it...")
        storage_bucket = storage_client.create_bucket(
            bucket_name,
            location=LOCATION,
        )

    return storage_bucket
