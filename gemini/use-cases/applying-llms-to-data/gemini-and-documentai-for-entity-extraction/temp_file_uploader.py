import uuid

from google.cloud import storage


class TempFileUploader:
    """Class with methods to work with files in GCS"""

    def __init__(self, gcs_temp_uri: str) -> None:
        path_parts = gcs_temp_uri.replace("gs://", "").split("/")
        self.temp_bucket_name = path_parts[0]
        self.temp_file_path_gcs = "/".join(path_parts[1:])
        self.storage_client = storage.Client()
        self.destination_blob_name = ""

    def _get_destination_blob_name(self, file_path: str) -> str:
        file_id = str(uuid.uuid4())
        file_extension = file_path.split(".")[-1]
        destination_blob_name = f"{self.temp_file_path_gcs}{file_id}.{file_extension}"
        return destination_blob_name

    def upload_file(self, file_path: str) -> str:
        """Function to upload file to GCS"""
        self.destination_blob_name = self._get_destination_blob_name(file_path)

        bucket = self.storage_client.bucket(self.temp_bucket_name)
        blob = bucket.blob(self.destination_blob_name)
        blob.upload_from_filename(file_path)

        gcs_destination_uri = (
            f"gs://{self.temp_bucket_name}/{self.destination_blob_name}"
        )
        return gcs_destination_uri

    def delete_file(self) -> None:
        """Function to delete the temporary file from GCS"""
        if self.destination_blob_name:
            bucket = self.storage_client.bucket(self.temp_bucket_name)
            blob = bucket.blob(self.destination_blob_name)
            blob.delete()
