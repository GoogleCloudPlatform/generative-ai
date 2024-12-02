from typing import List
from google.cloud.storage import Client, Blob

BASE_BUCKET="quick-bot"
EMBEDDINGS_FILE="embeddings.json"
EMBEDDINGS_FOLDER="embeddings"

CONTENT_TYPE="text/plain"

class CloudStorageRepository:

    def __init__(self, project_id: str):
        self.client = Client()
        self.bucket_name = f"{BASE_BUCKET}-{project_id}"
        self.bucket = self.client.bucket(self.bucket_name)
    
    def create(self, resource_name: str, content: str):
        new_blob = self.bucket.blob(resource_name)
        new_blob.content_type = CONTENT_TYPE
        new_blob.upload_from_string(content)