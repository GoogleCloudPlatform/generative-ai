"""
This module provides functions for interacting with the Google Cloud Storage
bucket, specifically for managing projects and their associated files.
This module:
    * Retrieves a list of existing projects from the GCS bucket.
    * Updates the project list stored in the GCS bucket.
    * Lists PDF, text, and other supported file types in the current
      project's GCS bucket.
    * Deletes an entire project and its contents from the GCS bucket.
    * Deletes a specific file from the GCS project.
"""

# pylint: disable=E0401

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from google.cloud import storage
import pandas as pd
import streamlit as st

load_dotenv()

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket("product_innovation_bucket")


def list_pdf_files_gcs() -> list[list[Any]]:
    """Lists the PDF files in the current project's GCS bucket.

    This function lists the PDF files in the current project's GCS bucket.
    It uses the 'storage_client' to get the list of blobs in the bucket and
    then filters the list to only include PDF files.
    It then returns a list of tuples of the blob name and the file extension.

    Returns:
        list[list[Any]]: A list of tuples of the blob name and the file
        extension.
    """
    blob = bucket.blob(f"{st.session_state.product_category}/embeddings.json")
    files = []
    if blob.exists():
        blobs = bucket.list_blobs(prefix=f"{st.session_state.product_category}/")
        for blob in blobs:
            _, file_extension = os.path.splitext(blob.name)
            if file_extension in (".pdf", ".txt", ".csv", ".docx"):
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
    blobs = bucket.list_blobs(prefix=f"{st.session_state.product_category}/")
    for blob in blobs:
        blob.delete()
    st.session_state.product_categories.remove(st.session_state.product_category)
    if len(st.session_state.product_categories) >= 1:
        st.session_state.product_category = st.session_state.product_categories[0]

    project_list_blob = bucket.blob("project_list.txt")
    project_list_blob.upload_from_string(
        json.dumps(st.session_state.product_categories)
    )
    st.rerun()


def delete_file_from_gcs(file_name: str) -> None:
    """Deletes a file from the GCS bucket.

    This function deletes a file from the GCS bucket.
    It uses the 'storage_client' to get the 'blob' object for the file and
    then deletes the blob.

    Args:
        file_name (str): The name of the file to delete.
    """
    file_blob = bucket.blob(f"{st.session_state.product_category}/{file_name}")
    file_blob.delete()
    blob = bucket.blob(st.session_state.product_category + "/embeddings.json")
    stored_embedding_data = blob.download_as_string()
    dff = pd.DataFrame.from_dict(json.loads(stored_embedding_data))
    dff = dff.drop(dff[dff["file_name"] == file_name].index)
    dff.reset_index(inplace=True, drop=True)
    bucket.blob(
        f"{st.session_state.product_category}/embeddings.json"
    ).upload_from_string(dff.to_json(), "application/json")
