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

import json
import logging
import os
from typing import Any

from app.pages_utils.pages_config import GLOBAL_CFG
from dotenv import load_dotenv
from google.cloud import storage
import pandas as pd
import streamlit as st

load_dotenv()

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# Define storage bucket
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(GLOBAL_CFG["bucket_name"])


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
    project_embedding = bucket.blob(
        f"{st.session_state.product_category}/embeddings.json"
    )
    files = []
    if project_embedding.exists():
        file_list = bucket.list_blobs(prefix=f"{st.session_state.product_category}/")
        for file in file_list:
            _, file_extension = os.path.splitext(file.name)
            if file_extension in (".pdf", ".txt", ".csv", ".docx"):
                files.append([file.name, file_extension])
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
    # Load list of files for current project.
    project_file_list = bucket.list_blobs(
        prefix=f"{st.session_state.product_category}/"
    )

    # Delete the files in the project.
    for file in project_file_list:
        file.delete()

    # Remove the project name corresponding to the deleted project.
    st.session_state.product_categories.remove(st.session_state.product_category)

    # Reset selected project to next project in list.
    if len(st.session_state.product_categories) >= 1:
        st.session_state.product_category = st.session_state.product_categories[0]

    # Update list of projects.
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
    # Load and delete embeddings of deleted file.
    deleted_file_blob = bucket.blob(f"{st.session_state.product_category}/{file_name}")
    deleted_file_blob.delete()

    # Load embeddings of the project
    project_embeddings = bucket.blob(
        st.session_state.product_category + "/embeddings.json"
    )
    stored_embedding_data = project_embeddings.download_as_string()
    embeddings_df = pd.DataFrame.from_dict(json.loads(stored_embedding_data))

    # Remove deleted file from project embeddings.
    embeddings_df = embeddings_df.drop(
        embeddings_df[embeddings_df["file_name"] == file_name].index
    )
    embeddings_df.reset_index(inplace=True, drop=True)

    # Update embeddings in GCS.
    bucket.blob(
        f"{st.session_state.product_category}/embeddings.json"
    ).upload_from_string(embeddings_df.to_json(), "application/json")
