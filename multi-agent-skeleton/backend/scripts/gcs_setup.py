from google.cloud.storage import Client


def create_bucket(bucket_name: str, location: str, storage_client: Client):
    storage_bucket = storage_client.bucket(bucket_name)
    if not storage_bucket.exists():
        print(f"{bucket_name} Bucket does not exist, creating it...")
        storage_bucket = storage_client.create_bucket(
            bucket_name,
            location=location,
        )

    return storage_bucket
