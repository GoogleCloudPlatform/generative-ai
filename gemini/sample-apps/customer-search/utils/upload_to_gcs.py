from google.cloud import storage


def upload_blob(
    bucket_name: str, source_file_name: str, destination_blob_name: str
) -> str:
    """
    Uploads a file to a Google Cloud Storage bucket.

    Args:
        bucket_name (str): The name of the bucket to upload the file to.
        source_file_name (str): The name of the file to upload.
        destination_blob_name (str): The name of the blob to create in the bucket.

    Returns:
        The public URL of the uploaded file.
    """

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")
    return blob.public_url