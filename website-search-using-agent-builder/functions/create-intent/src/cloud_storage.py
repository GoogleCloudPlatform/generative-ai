"""Provides a repository class for interacting with Google Cloud Storage."""
from google.cloud.storage import Client

BASE_BUCKET = "quick-bot"
EMBEDDINGS_FILE = "embeddings.json"
EMBEDDINGS_FOLDER = "embeddings"

CONTENT_TYPE = "text/plain"


class CloudStorageRepository:
    """
    Provides an interface for interacting with Google Cloud Storage (GCS).
    """

    def __init__(self, project_id: str):
        """
        Initializes the CloudStorageRepository.

        Args:
            project_id: The Google Cloud project ID.
            bucket_name: The name of the GCS bucket to interact with. If None,
                         it might be inferred from environment variables or defaults,
                         or you might need to set it later or pass it to methods.
                         *It's generally better to require it here or have a default.*
                         Assuming it's derived from project_id for this example.
        """
        self.client = Client()
        self.bucket_name = f"{BASE_BUCKET}-{project_id}"
        self.bucket = self.client.bucket(self.bucket_name)

    def create(self, resource_name: str, content: str):
        """
        Creates or overwrites a blob in the GCS bucket with the given string contents.

        Args:
            destination_blob_name: The full path (including filename) for the blob
                                   within the bucket (e.g., 'folder/subfolder/file.txt').
            contents: The string data to write to the blob.
        """
        new_blob = self.bucket.blob(resource_name)
        new_blob.content_type = CONTENT_TYPE
        new_blob.upload_from_string(content)
