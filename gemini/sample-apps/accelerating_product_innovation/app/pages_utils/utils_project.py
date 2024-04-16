"""
This module provides functions for interacting with the Google Cloud Storage (GCS)
bucket, specifically for managing projects and their associated files.  
This module:
    * Retrieves a list of existing projects from the GCS bucket. 
    * Updates the project list stored in the GCS bucket.
    * Lists PDF, text, and other supported file types in the current project's GCS bucket. 
    * Deletes an entire project and its contents from the GCS bucket.
    * Deletes a specific file from the GCS project.
"""

import json
import logging
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

logging.basicConfig(
    format="%(levelname)s:%(message)s", level=logging.DEBUG
)

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")


def get_projects_list():
    """Gets the list of projects from the 'project_list.txt' file in the
    'product_innovation_bucket' GCS bucket.

    This function gets the list of projects from the 'project_list.txt'
    file in the 'product_innovation_bucket' GCS bucket. It uses the
    'storage_client' to get the 'blob' object for the 'project_list.txt'
    file and then downloads the contents of the blob as a string.
    It then loads the contents of the string as a JSON object and returns
    the list of projects.

    Returns:
        list[str]: The list of projects.
    """
    project_id = PROJECT_ID
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket("product_innovation_bucket")
    blob = bucket.blob("project_list.txt")
    blob_content = blob.download_as_string()
    return json.loads(blob_content)


def update_projects(my_list: list[str]) -> None:
    """Updates the list of projects in the 'project_list.txt'
    file in the 'product_innovation_bucket' GCS bucket.

    This function updates the list of projects in the 'project_list.txt'
    file in the 'product_innovation_bucket' GCS bucket.
    It uses the 'storage_client' to get the 'blob' object for the 'project_list.txt'
    file and then uploads the contents of the list as a string to the blob.

    Args:
        my_list (list[str]): The list of projects to update.
    """
    project_id = PROJECT_ID
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket("product_innovation_bucket")
    blob = bucket.blob("project_list.txt")
    list_string = json.dumps(my_list)
    blob.upload_from_string(list_string)


def list_pdf_files_gcs() -> list[tuple[str, str]]:
    """Lists the PDF files in the current project's GCS bucket.

    This function lists the PDF files in the current project's GCS bucket.
    It uses the 'storage_client' to get the list of blobs in the bucket and
    then filters the list to only include PDF files.
    It then returns a list of tuples of the blob name and the file extension.

    Returns:
        list[tuple[str, str]]: A list of tuples of the blob name and the file extension.
    """
    project_id = PROJECT_ID
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket("product_innovation_bucket")
    blob = bucket.blob(
        f"{st.session_state.product_category}/embeddings.json"
    )
    files = []
    if blob.exists():
        blobs = storage_client.list_blobs(
            "product_innovation_bucket",
            prefix=f"{st.session_state.product_category}/",
        )
        for blob in blobs:
            _, file_extension = os.path.splitext(blob.name)
            if (
                file_extension == ".pdf"
                or file_extension == ".txt"
                or file_extension == ".csv"
                or file_extension == ".docx"
            ):
                files.append([blob.name, file_extension])
    else:
        st.write("No file uploaded")
    return files


def delete_project_from_gcs() -> None:
    """Deletes the current project from the GCS bucket.

    This function deletes the current project from the GCS bucket.
    It uses the 'storage_client' to get the list of blobs in the bucket
    and then deletes all of the blobs in the bucket.
    It then removes the current project from the list of projects and
    updates the 'project_list.txt' file in the GCS bucket.
    """
    project_id = PROJECT_ID
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket("product_innovation_bucket")
    blobs = bucket.list_blobs(
        prefix=f"{st.session_state.product_category}/"
    )
    for blob in blobs:
        blob.delete()
    st.session_state.product_categories.remove(
        st.session_state.product_category
    )
    if len(st.session_state.product_categories) >= 1:
        st.session_state.product_category = (
            st.session_state.product_categories[0]
        )
    update_projects(st.session_state.product_categories)
    st.rerun()


def delete_file_from_gcs(file_name: str) -> None:
    """Deletes a file from the GCS bucket.

    This function deletes a file from the GCS bucket.
    It uses the 'storage_client' to get the 'blob' object for the file and then deletes the blob.

    Args:
        file_name (str): The name of the file to delete.
    """

    project_id = PROJECT_ID
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket("product_innovation_bucket")
    file_blob = bucket.blob(
        f"{st.session_state.product_category}/{file_name}"
    )
    file_blob.delete()
    blob = bucket.blob(
        st.session_state.product_category + "/embeddings.json"
    )
    stored_embedding_data = blob.download_as_string()
    dff = pd.DataFrame.from_dict(json.loads(stored_embedding_data))
    dff = dff.drop(dff[dff["file_name"] == file_name].index)
    dff.reset_index(inplace=True, drop=True)
    bucket.blob(
        f"{st.session_state.product_category}/embeddings.json"
    ).upload_from_string(dff.to_json(), "application/json")


def get_file_contents(file_name: str) -> bytes:
    """Gets the contents of a file from the GCS bucket.

    This function gets the contents of a file from the GCS bucket.
    It uses the 'storage_client' to get the 'blob' object for the
    file and then downloads the contents of the blob as a string.

    Args:
        file_name (str): The name of the file to get the contents of.

    Returns:
        bytes: The contents of the file.
    """
    project_id = PROJECT_ID
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket("product_innovation_bucket")
    blob = bucket.blob(
        f"{st.session_state.product_category}/{file_name}"
    )
    return blob.download_as_string()
