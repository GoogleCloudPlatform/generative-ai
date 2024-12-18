from google.cloud.storage import Client as GCSClient
import re

CONTENT_TYPE="text/plain"
LOCATION="us-central1"

class CloudStorageRepository:

    def __init__(self):
        self.client = GCSClient()
    
    def extract_bucket_name(gcs_url):
        """
        Extract the bucket name from a GCS URL.
        """
        match = re.match(r"gs://([^/]+)/", gcs_url)
        if match:
            return match.group(1)
        else:
            raise ValueError(f"Invalid GCS URL: {gcs_url}")
        

    def configure_bucket_cors(self, gcs_url):
        bucket_name = self.extract_bucket_name(gcs_url)
        storage_bucket = self.client.bucket(bucket_name)

        # Define CORS settings
        cors_configuration = [
            {
                "origin": ["*"],  # Allow all origins
                "method": ["GET", "POST", "HEAD"],  # Allowed HTTP methods
                "responseHeader": ["Content-Type", "Authorization"],  # Allowed response headers
                "maxAgeSeconds": 3600,  # Cache duration for preflight responses
            }
        ]

        # Set the bucket's CORS configuration
        storage_bucket.cors = cors_configuration
        storage_bucket.patch()  # Apply the changes

        print(f"CORS settings updated for bucket {bucket_name}")    