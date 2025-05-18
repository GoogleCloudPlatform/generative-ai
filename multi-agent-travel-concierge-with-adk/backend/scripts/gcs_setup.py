from google.cloud.storage import Client
from google.cloud.storage.bucket import Bucket

def create_bucket(bucket_name: str, location: str, storage_client: Client) -> Bucket:
    storage_bucket = storage_client.bucket(bucket_name)
    if not storage_bucket.exists():
        print(f"{bucket_name} Bucket does not exist, creating it...")
        storage_bucket = storage_client.create_bucket(
            bucket_name,
            location=location,
        )
        print(f"Successfully created bucket {storage_bucket.name}")

    return storage_bucket
