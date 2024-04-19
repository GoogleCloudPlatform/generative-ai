import json
import pickle

from google.cloud import storage


def create_json(json_object, filename, bucket_name):
    """Creates a JSON object in Google Cloud Storage.

    Args:
        json_object (dict): The JSON object to create.
        filename (str): The name of the file to create.
        bucket_name (str): The name of the bucket to create the file in.

    Returns:
        dict: A dictionary containing the response from the GCS API.
    """

    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    # create a blob
    blob = bucket.blob(filename)
    # upload the blob
    blob.upload_from_string(
        data=json.dumps(json_object), content_type="application/json"
    )
    result = filename + " upload complete"
    return {"response": result}


def upload_to_gcs(content, filename, bucket_name):
    """Uploads a file to Google Cloud Storage.

    Args:
        content (bytes): The contents of the file to upload.
        filename (str): The name of the file to upload.
        bucket_name (str): The name of the bucket to upload the file to.
    """
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)

    blob = bucket.blob(filename)
    with blob.open(mode="wb") as f:
        pickle.dump(content, f)


def upload_file(path, filename, bucket_name, folder):
    """Uploads a file to Google Cloud Storage.

    Args:
        path (str): The path to the file to upload.
        filename (str): The name of the file to upload.
        bucket_name (str): The name of the bucket to upload the file to.
        folder (str): The folder to upload the file to.
    """
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)

    blob = bucket.blob(folder + "/" + filename)

    blob.upload_from_filename(path)


def filesFromFolder(bucket_name, folder):
    """Lists all the files in a folder in Google Cloud Storage.

    Args:
        bucket_name (str): The name of the bucket to list the files in.
        folder (str): The name of the folder to list the files in.

    Returns:
        list: A list of the files in the folder.
    """
    client = storage.Client()
    return client.list_blobs(bucket_name, prefix=folder)


def get_from_gcs(filename, bucket_name):
    """Downloads a file from Google Cloud Storage.

    Args:
        filename (str): The name of the file to download.
        bucket_name (str): The name of the bucket to download the file from.

    Returns:
        bytes: The contents of the file.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)

    with blob.open(mode="rb") as f:
        loaded_file = pickle.load(f)

    return loaded_file


def get_json(bucket_name, filename):
    """Gets a JSON object from Google Cloud Storage.

    Args:
        bucket_name (str): The name of the bucket to get the file from.
        filename (str): The name of the file to get.

    Returns:
        dict: The JSON object.
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    # get the blob
    blob = bucket.get_blob(filename)
    # load blob using json
    file_data = json.loads(blob.download_as_string())
    return file_data


def list_jpg_files_in_bucket(bucket_name, folder_path):
    """Lists all the JPG files in a folder in Google Cloud Storage.

    Args:
        bucket_name (str): The name of the bucket to list the files in.
        folder_path (str): The path to the folder to list the files in.

    Returns:
        list: A list of the JPG files in the folder.
    """
    # Initialize GCS client
    client = storage.Client()

    # Get bucket object
    bucket = client.get_bucket(bucket_name)

    # List files in the given folder_path
    blobs = bucket.list_blobs(prefix=folder_path)

    # Filter .jpg files
    jpg_files = [
        blob.name.split("/")[-1] for blob in blobs if blob.name.endswith(".jpg")
    ]

    return jpg_files


def list_txt_files_in_bucket(bucket_name, folder_path):
    """Lists all the TXT files in a folder in Google Cloud Storage.

    Args:
        bucket_name (str): The name of the bucket to list the files in.
        folder_path (str): The path to the folder to list the files in.

    Returns:
        list: A list of the TXT files in the folder.
    """
    # Initialize GCS client
    client = storage.Client()

    # Get bucket object
    bucket = client.get_bucket(bucket_name)

    # List files in the given folder_path
    blobs = bucket.list_blobs(prefix=folder_path)

    # Filter .txt files
    txt_files = [
        blob.name.split("/")[-1] for blob in blobs if blob.name.endswith(".txt")
    ]

    return txt_files
