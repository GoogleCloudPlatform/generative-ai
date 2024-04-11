"""Function to write metadata for new pdf documents"""

import os
from pathlib import Path
import uuid

import functions_framework
from google.cloud import storage


@functions_framework.cloud_event
def write_metadata(cloud_event):
    """Main function"""
    # Set event vars
    data = cloud_event.data
    event_id = cloud_event["id"]
    event_type = cloud_event["type"]
    bucket = data["bucket"]
    name = data["name"]
    metageneration = data["metageneration"]
    timeCreated = data["timeCreated"]
    updated = data["updated"]

    # Print event vars to log
    print(f"Event ID: {event_id}")
    print(f"Event type: {event_type}")
    print(f"Bucket: {bucket}")
    print(f"File: {name}")
    print(f"Metageneration: {metageneration}")
    print(f"Created: {timeCreated}")
    print(f"Updated: {updated}")

    # Set local vars
    project_id = os.environ["PROJECT_ID"]
    metadata_bucket = f"{project_id}-docs-metadata"
    uid = str(uuid.uuid4())
    ticker = Path(name).stem
    target_file_name = f"{ticker}.jsonl"

    # Build metadata jsonl
    metadata = (
        '{"id":"'
        + uid
        + '","structData":{"ticker":"'
        + ticker
        + '"},"content":{"mimeType":"application/pdf","uri":"gs://'
        + bucket
        + "/"
        + name
        + '"}}'
    )

    # Write jsonl to metadata bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(metadata_bucket)
    blob = bucket.blob(target_file_name)

    with blob.open("w") as f:
        f.write(metadata)

    print(f"Metadata for {ticker} written to {metadata_bucket}")
    print(f"Metadata object: {metadata}")
    storage_client.close()
