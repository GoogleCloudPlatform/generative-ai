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


def files_from_folder(bucket_name, folder):
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
