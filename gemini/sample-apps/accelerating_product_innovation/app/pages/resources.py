"""
This module manages the "Resources" page of the Streamlit application. Key
functionalities include:

* Project Management:
    * Displays existing projects.
    * Allows users to add new project categories.
* File Management:
    * Enables file uploads (txt, docx, pdf, csv).
    * Handles conversion and storage of uploaded files.
    * Lists stored project files.
    * Provides download and delete options for stored files.
"""

# pylint: disable=E0401

import json
import os

from app.pages_utils import project, resources_store_embeddings, setup
from app.pages_utils.pages_config import GLOBAL_CFG, PAGES_CFG
from google.cloud import storage
import streamlit as st

# Get the page configuration from the config file
page_cfg = PAGES_CFG["1_Resources"]
setup.page_setup(page_cfg)


PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# Define storage bucket
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(GLOBAL_CFG["bucket_name"])


# Initialize project form submission state if not already initialized
if "project_form_submitted" not in st.session_state:
    st.session_state.project_form_submitted = False


@st.cache_data
def get_resources_img() -> None:
    """
    Loads, displays and caches the resources header image.

    Returns: None.
    """
    # Get the file path of the resources image
    page_images = [page_cfg["resources_img"]]
    for page_image in page_images:
        st.image(page_image)


# Display header image.
get_resources_img()

# Create a container for the screen
screen = st.container()

# Create a form for the resources page
with st.form(key="resources_form", clear_on_submit=True):
    # Display the projects
    setup.display_projects()

    # Add a text input field for adding a new project category
    st.session_state.new_product_category_added = st.text_input(
        "",
        key="000",
        placeholder="Add a new project",
    )

    # Add a file uploader for uploading files
    st.session_state.uploaded_files = st.file_uploader(
        "",
        type=["txt", "docx", "pdf", "csv"],
        accept_multiple_files=True,
        key="09",
    )

    # Add a submit button to the form
    submitted = st.form_submit_button("Submit", type="primary")

# Check if the form was submitted
if submitted:
    st.session_state.project_form_submitted = True
    # Check if a new project category was added
    if (
        st.session_state.new_product_category_added is not None
        and st.session_state.new_product_category_added != ""
    ):
        # Update the product category list
        st.session_state.product_category = st.session_state.new_product_category_added
        st.session_state.product_categories = [
            st.session_state.new_product_category_added
        ] + st.session_state.product_categories

        # Update the projects in GCS
        project_list_blob = bucket.blob("project_list.txt")
        project_list_blob.upload_from_string(
            json.dumps(st.session_state.product_categories)
        )

        # Reset the new project category field
        st.session_state.new_product_category_added = None

        # Check if files were uploaded
        if st.session_state.uploaded_files is not None:
            # Convert the uploaded files to data packets and upload them to GCS
            for uploaded_file in st.session_state.uploaded_files:
                resources_store_embeddings.create_and_store_embeddings(uploaded_file)

    # Check if files were uploaded
    if st.session_state.uploaded_files is not None:
        # Convert the uploaded files to data packets and upload them to GCS
        for uploaded_file in st.session_state.uploaded_files:
            resources_store_embeddings.create_and_store_embeddings(uploaded_file)


# Check if the project form was submitted and the file upload is complete
if st.session_state.project_form_submitted is True:
    # Create columns for the project heading and delete button
    project_heading = st.columns([4, 1])

    # Display the project category heading
    with project_heading[0]:
        st.markdown(
            f"""<h3 style = 'text-align: center; color: #6a90e2;'>
            {st.session_state.product_category}</h3>""",
            unsafe_allow_html=True,
        )

    # Add a delete button for the project
    with project_heading[1]:
        if st.button("Delete this project", type="primary"):
            # Display a spinner while deleting the project
            with st.spinner("Deleting Project..."):
                # Delete the project from GCS
                project.delete_project_from_gcs()

    # List the PDF files in the GCS bucket
    files = project.list_pdf_files_gcs()

    # Get the length of the product category name
    len_prod_cat = len(st.session_state.product_category) + 1

    # Display the files in a spinner
    with st.spinner("Fetching Files"):
        # Set the border style for the file list items
        BORDER_STYLE = "border: 2px solid black; padding: 10px;"

        # Iterate over the files
        for color_counter, file in enumerate(files):
            # Create columns for the file name, download button, and
            # delete button
            list_files_columns = st.columns([15, 1, 1])

            # Set a color counter to alternate the background color of the file.
            with list_files_columns[0]:
                if color_counter % 2 == 0:
                    BACKGROUND_COLOR = "#e6f2ff"
                else:
                    BACKGROUND_COLOR = "white"
                st.write(
                    f"""<div style=
                        'background-color: {BACKGROUND_COLOR};
                        padding: 10px;
                        margin-bottom: 0px;
                        margin-top: 0px;
                        border-radius:10px;'>{file[0][len_prod_cat:]}</div>""",
                    unsafe_allow_html=True,
                )

            # Add a download button for the file
            file_content_blob = bucket.blob(
                f"{st.session_state.product_category}/{file[0][len_prod_cat:]}"
            )
            file_contents = file_content_blob.download_as_string()
            with list_files_columns[1]:
                st.download_button(
                    label=":arrow_down:",
                    data=file_contents,
                    file_name=file[0][len_prod_cat:],
                    mime=file[1],
                )

            # Add a delete button for the file
            with list_files_columns[2]:
                if st.button(
                    ":x:",
                    key=file[0][len_prod_cat:],
                ):
                    project.delete_file_from_gcs(file_name=file[0][len_prod_cat:])
