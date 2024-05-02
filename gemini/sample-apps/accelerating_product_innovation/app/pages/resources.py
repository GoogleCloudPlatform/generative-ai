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

from app.pages_utils import (
    utils,
    utils_project,
    utils_resources_store_embeddings,
)
from app.pages_utils.utils_config import PAGES_CFG
import streamlit as st

# Get the page configuration from the config file
page_cfg = PAGES_CFG["1_Resources"]
utils.page_setup(page_cfg)

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
    utils.display_projects()

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
        st.session_state.product_category = (
            st.session_state.new_product_category_added
        )
        st.session_state.product_categories = [
            st.session_state.new_product_category_added
        ] + st.session_state.product_categories

        # Update the projects in GCS
        utils_project.update_projects(st.session_state.product_categories)

        # Reset the new project category field
        st.session_state.new_product_category_added = None

        # Check if files were uploaded
        if st.session_state.uploaded_files is not None:
            # Convert the uploaded files to data packets and upload them to GCS
            for uploaded_file in st.session_state.uploaded_files:
                utils_resources_store_embeddings.convert_file_to_data_packets(
                    uploaded_file
                )

    # Check if files were uploaded
    if st.session_state.uploaded_files is not None:
        # Convert the uploaded files to data packets and upload them to GCS
        for uploaded_file in st.session_state.uploaded_files:
            utils_resources_store_embeddings.convert_file_to_data_packets(
                uploaded_file
            )


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
                utils_project.delete_project_from_gcs()

    # List the PDF files in the GCS bucket
    files = utils_project.list_pdf_files_gcs()

    # Get the length of the product category name
    len_prod_cat = len(st.session_state.product_category) + 1

    # Display the files in a spinner
    with st.spinner("Fetching Files"):
        # Set a color counter to alternate the background color of the file
        # list items
        color_counter = 0

        # Set the border style for the file list items
        BORDER_STYLE = "border: 2px solid black; padding: 10px;"

        # Iterate over the files
        for file in files:
            # Create columns for the file name, download button, and
            # delete button
            list_files_columns = st.columns([15, 1, 1])

            # Display the file name
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
                color_counter += 1

            # Add a download button for the file
            with list_files_columns[1]:
                st.download_button(
                    label=":arrow_down:",
                    data=utils_project.get_file_contents(
                        file[0][len_prod_cat:]
                    ),
                    file_name=file[0][len_prod_cat:],
                    mime=file[1],
                )

            # Add a delete button for the file
            with list_files_columns[2]:
                if st.button(
                    ":x:",
                    key=file[0][len_prod_cat:],
                ):
                    utils_project.delete_file_from_gcs(
                        file_name=file[0][len_prod_cat:]
                    )
