# Copyright 2024 Google, LLC. This software is provided as-is, without
# warranty or representation for any use or purpose. Your use of it is
# subject to your agreement with Google.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
GCP Download utilities
"""
import logging
import os
import re

from google.cloud import storage
from llama_index.core.schema import NodeRelationship, RelatedNodeInfo
import yaml

logging.basicConfig(level=logging.INFO)  # Set the desired logging level
logger = logging.getLogger(__name__)


# Function to load the configuration
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)


# Load the configuration
config = load_config()
# Get the DATA_PATH from the config
DATA_PATH = config["data_path"]


class Blob:
    def __init__(self, path: str, mimetype: str):
        self.path = path
        self.mimetype = mimetype


def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"

    # The ID of your GCS object
    # source_blob_name = "storage-object-name"

    # The path to which the file should be downloaded
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(
        f"Downloaded storage object {source_blob_name} \
          from bucket {bucket_name} to local file {destination_file_name}."
    )


def download_bucket_with_transfer_manager(
    bucket_name,
    prefix,
    delimiter=None,
    destination_directory="",
    workers=8,
    max_results=1000,
):
    """Download all of the blobs in a bucket, concurrently in a process pool.

    The filename of each blob once downloaded is derived from the blob name and
    the `destination_directory `parameter. For complete control of the filename
    of each blob, use transfer_manager.download_many() instead.

    Directories will be created automatically as needed, for instance to
    accommodate blob names that include slashes.
    """

    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"

    # The directory on your computer to which to download all of the files. This
    # string is prepended (with os.path.join()) to the name of each blob to form
    # the full path. Relative paths and absolute paths are both accepted. An
    # empty string means "the current working directory". Note that this
    # parameter allows accepts directory traversal ("../" etc.) and is not
    # intended for unsanitized end user input.
    # destination_directory = ""

    # The maximum number of processes to use for the operation. The performance
    # impact of this value depends on the use case, but smaller files usually
    # benefit from a higher number of processes. Each additional process occupies
    # some CPU and memory resources until finished. Threads can be used instead
    # of processes by passing `worker_type=transfer_manager.THREAD`.
    # workers=8

    # The maximum number of results to fetch from bucket.list_blobs(). This
    # sample code fetches all of the blobs up to max_results and queues them all
    # for download at once. Though they will still be executed in batches up to
    # the processes limit, queueing them all at once can be taxing on system
    # memory if buckets are very large. Adjust max_results as needed for your
    # system environment, or set it to None if you are sure the bucket is not
    # too large to hold in memory easily.
    # max_results=1000

    from google.cloud.storage import transfer_manager

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob_names = [
        blob.name
        for blob in bucket.list_blobs(
            prefix=prefix, delimiter=delimiter, max_results=max_results
        )
    ]

    results = transfer_manager.download_many_to_path(
        bucket,
        blob_names,
        destination_directory=destination_directory,
        max_workers=workers,
    )

    for name, result in zip(blob_names, results):
        # The results list is either `None` or an exception for each blob in
        # the input list, in order.

        if isinstance(result, Exception):
            logger.info(f"Failed to download {name} due to exception: {result}")
        else:
            logger.info(f"Downloaded {name} to {destination_directory + name}.")


def link_nodes(node_list):
    for i, current_node in enumerate(node_list):
        if i > 0:  # Not the first node
            previous_node = node_list[i - 1]
            current_node.relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(
                node_id=previous_node.node_id
            )

        if i < len(node_list) - 1:  # Not the last node
            next_node = node_list[i + 1]
            current_node.relationships[NodeRelationship.NEXT] = RelatedNodeInfo(
                node_id=next_node.node_id
            )
    return node_list


def create_pdf_blob_list(bucket_name, prefix):
    """
    Create a list of Blob objects for processing.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    logger.info(blobs)
    return [
        Blob(
            path=f"gs://{bucket_name}/{blob.name}",
            mimetype=blob.content_type or "application/pdf",
        )
        for blob in blobs
        if blob.name.lower().endswith(".pdf")
    ]


def upload_directory_to_gcs(local_dir_path: str, bucket_name: str, prefix: str):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    for root, dirs, files in os.walk(local_dir_path):
        for file in files:
            local_file_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_file_path, local_dir_path)
            gcs_blob_name = f"{prefix}/{relative_path}"

            blob = bucket.blob(gcs_blob_name)
            blob.upload_from_filename(local_file_path)
            print(f"File {local_file_path} uploaded to {gcs_blob_name}")


def clean_text(text):
    """
    Clean and preprocess the extracted text.
    """

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Remove any non-printable characters
    text = "".join(char for char in text if char.isprintable() or char.isspace())
    print(f"Cleaned text length: {len(text)}")

    return text
