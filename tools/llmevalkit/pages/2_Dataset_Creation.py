# Copyright 2025 Google LLC
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#     https://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language

"""Streamlit page for creating and managing datasets in Google Cloud Storage."""

import logging
import os

import streamlit as st
from dotenv import load_dotenv
from google.cloud import storage
from streamlit.runtime.uploaded_file_manager import UploadedFile

# Load environment variables from .env file
load_dotenv("src/.env")

# Configure logging to the console
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@st.cache_data(ttl=300)
def get_existing_datasets(
    _storage_client: storage.Client, bucket_name: str
) -> list[str]:
    """Lists 'directories' in GCS under the 'datasets/' prefix.
    These directories represent the existing datasets.
    """
    if not bucket_name or not _storage_client:
        return []

    bucket = _storage_client.bucket(bucket_name)
    prefix = "datasets/"
    retrieved_prefixes = set()

    try:
        # Explicitly iterate through pages for robustness.
        iterator = bucket.list_blobs(prefix=prefix, delimiter="/")
        for page in iterator.pages:
            retrieved_prefixes.update(page.prefixes)

        # The retrieved prefixes are the "subdirectories".
        # e.g., {'datasets/my_dataset_1/', 'datasets/my_dataset_2/'}
        dir_names = []
        for p in retrieved_prefixes:
            # Extract 'my_dataset_1' from 'datasets/my_dataset_1/'
            name = p[len(prefix) :].strip("/")
            if name:
                dir_names.append(name)
        logger.info(f"Found datasets: {dir_names}")
        return sorted(dir_names)
    except Exception as e:
        st.error(f"Error listing datasets from GCS: {e}")
        logger.error(f"Error in get_existing_datasets: {e}", exc_info=True)
        return []


def _handle_upload(
    storage_client: storage.Client,
    bucket_name: str,
    dataset_name: str,
    uploaded_file: UploadedFile,
) -> None:
    """Handles the logic of uploading a file to GCS."""
    if not all([storage_client, bucket_name, dataset_name, uploaded_file]):
        st.warning("Missing required information for upload.")
        return

    try:
        file_name = uploaded_file.name
        content_type = "text/plain"  # Default
        if file_name.endswith(".csv"):
            content_type = "text/csv"
        elif file_name.endswith(".json"):
            content_type = "application/json"
        elif file_name.endswith(".jsonl"):
            content_type = "application/x-jsonlines"

        blob_path = f"datasets/{dataset_name}/{uploaded_file.name}"
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        with st.spinner(f"Uploading '{uploaded_file.name}' to '{dataset_name}'..."):
            blob.upload_from_string(uploaded_file.getvalue(), content_type=content_type)

        st.success(
            f"Successfully uploaded '{uploaded_file.name}' to dataset '{dataset_name}'!"
        )
        logger.info(f"Uploaded file to gs://{bucket_name}/{blob_path}")
        # Clear the cache for get_existing_datasets to reflect the new dataset if created
        get_existing_datasets.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Failed to upload file: {e}")
        logger.error(f"Error during GCS upload: {e}", exc_info=True)


def _ensure_datasets_folder_exists(
    storage_client: storage.Client, bucket_name: str
) -> None:
    """Ensures the 'datasets/' folder exists by creating a placeholder object if needed.

    This helps it appear in the GCS UI even when empty.
    """
    if not storage_client or not bucket_name:
        return
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob("datasets/")
        if not blob.exists():
            blob.upload_from_string("", content_type="application/x-directory")
            logger.info(
                f"Created placeholder for 'datasets/' folder in bucket '{bucket_name}'."
            )
    except Exception as e:
        # This is not a critical failure, so just log a warning.
        logger.warning(f"Could not ensure 'datasets/' folder exists: {e}")


def main() -> None:
    """Renders the Dataset Creation page."""
    st.set_page_config(
        layout="wide", page_title="Dataset Management", page_icon="assets/favicon.ico"
    )

    # --- Initialize Session State & GCS Client ---
    if "storage_client" not in st.session_state:
        try:
            st.session_state.storage_client = storage.Client()
        except Exception as e:
            st.error(f"Could not connect to Google Cloud Storage: {e}")
            st.stop()

    BUCKET_NAME = os.getenv("BUCKET")
    if not BUCKET_NAME:
        st.error("BUCKET environment variable is not set. Please configure it in .env.")
        st.stop()

    # Ensure the base 'datasets/' folder exists for UI consistency
    _ensure_datasets_folder_exists(st.session_state.storage_client, BUCKET_NAME)

    st.title("Dataset Management")
    st.markdown(
        "Create new datasets or upload files (CSV, JSON, or JSONL) to existing ones. "
        "A 'Dataset' is a folder in your GCS bucket used to group related evaluation files."
    )
    st.divider()

    # --- Section 1: Upload File ---
    st.subheader("1. Upload a File")

    existing_datasets = get_existing_datasets(
        st.session_state.storage_client, BUCKET_NAME
    )

    # Let user choose whether to create a new dataset or add to an existing one
    upload_mode = st.radio(
        "Choose an action:",
        ("Create a new dataset", "Add to an existing dataset"),
        key="upload_mode",
        horizontal=True,
    )

    dataset_name = ""
    if upload_mode == "Create a new dataset":
        dataset_name = st.text_input(
            "Enter a name for the new dataset:",
            key="new_dataset_name",
            help="Use a descriptive name, e.g., 'sentiment_analysis_v1'.",
        )
    else:
        dataset_name = st.selectbox(
            "Select an existing dataset:",
            options=existing_datasets,
            key="selected_dataset_for_upload",
            help="Choose the dataset folder to upload your file into.",
            index=None,
            placeholder="Select a dataset...",
        )

    uploaded_file = st.file_uploader(
        "Select a file to upload",
        type=["csv", "json", "jsonl"],
        key="file_uploader",
    )

    if st.button("Upload to Cloud Storage", type="primary", use_container_width=True):
        if not dataset_name:
            st.warning("Please provide or select a dataset name.")
        elif not uploaded_file:
            st.warning("Please select a file to upload.")
        else:
            _handle_upload(
                st.session_state.storage_client,
                BUCKET_NAME,
                dataset_name,
                uploaded_file,
            )

    st.divider()

    # --- Section 2: View Existing Datasets ---
    st.subheader("2. View Existing Datasets")

    with st.expander("Browse datasets and their contents", expanded=True):
        selected_dataset_to_view = st.selectbox(
            "Select a dataset to view its contents:",
            options=existing_datasets,
            key="selected_dataset_for_view",
            index=None,
            placeholder="Select a dataset...",
        )

        if selected_dataset_to_view:
            prefix = f"datasets/{selected_dataset_to_view}/"
            blobs = st.session_state.storage_client.list_blobs(
                BUCKET_NAME, prefix=prefix
            )
            filenames = [
                os.path.basename(b.name)
                for b in blobs
                if b.name.endswith((".csv", ".json", ".jsonl"))
            ]

            if filenames:
                st.write(f"**Files in '{selected_dataset_to_view}':**")
                st.text_area(
                    "Files",
                    value="\n".join(filenames),
                    height=150,
                    disabled=True,
                    label_visibility="collapsed",
                )
            else:
                st.info(f"No files found in the '{selected_dataset_to_view}' dataset.")

    st.caption("LLM EvalKit | Dataset Management")


if __name__ == "__main__":
    main()
