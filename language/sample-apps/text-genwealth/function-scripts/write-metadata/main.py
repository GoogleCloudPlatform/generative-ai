import functions_framework
import uuid
from google.cloud import storage
from pathlib import Path
import os

@functions_framework.cloud_event
def write_metadata(cloud_event):
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
    project_id = os.environ['PROJECT_ID']
    metadata_bucket = "{}-docs-metadata".format(project_id)
    id = str(uuid.uuid4())
    ticker = Path(name).stem
    target_file_name = "{}.jsonl".format(ticker)

    # Build metadata jsonl
    metadata = '{"id":"' + id + '","structData":{"ticker":"' + ticker + '"},"content":{"mimeType":"application/pdf","uri":"gs://' + bucket + '/' + name + '"}}'
    
    # Write jsonl to metadata bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(metadata_bucket)
    blob = bucket.blob(target_file_name)

    with blob.open("w") as f:
        f.write(metadata)

    print("Metadata for {} written to {}".format(ticker, metadata_bucket))
    print("Metadata object: {}".format(metadata))
    storage_client.close()






