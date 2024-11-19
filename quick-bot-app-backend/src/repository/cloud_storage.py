from typing import List
from google.cloud.storage import Client, Blob

BUCKET="quick-bot"

INTENT_FOLDER="intents"
EMBEDDINGS_FILE="embeddings.json"
EMBEDDINGS_FOLDER="embeddings"

CONTENT_TYPE="text/plain"

class CloudStorageRepository:

    def __init__(self):
        self.client = Client()
    
    def list(self, full_path: str) -> List[Blob]:
        bucket = full_path.split("/")[2]
        prefix = full_path.replace(f"gs://{bucket}/", "")
        return list(self.client.list_blobs(bucket, prefix=prefix))