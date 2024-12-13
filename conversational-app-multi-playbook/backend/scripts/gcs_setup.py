from google.cloud.storage import Client as GCSClient
from scripts.big_query_setup import PROJECT_ID

BUCKET=f"quick-bot-{PROJECT_ID}"
CONTENT_TYPE="text/plain"
LOCATION="us-central1"

storage_client = GCSClient()

def create_bucket(bucket_name: str):
    storage_bucket = storage_client.bucket(bucket_name)
    if not storage_bucket.exists():
        print(f"{bucket_name} Bucket does not exist, creating it...")
        storage_bucket = storage_client.create_bucket(
            bucket_name,
            location=LOCATION,
        )
    
    return storage_bucket