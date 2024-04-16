"""
This module provides functions for downloading generated content (emails, product content) 
as zip archives.
"""

import base64
import io
import zipfile

import streamlit as st
import streamlit.components.v1 as components

from app.pages_utils.utils_content_gen import generate_email
from app.pages_utils.utils_export_content_pdf import (
    create_content_pdf,
)


def download_button(object_to_download, download_filename):
    """Generates a download link for the given object.

    Args:
        object_to_download (bytes or str): The object to download.
        download_filename (str): The filename of the downloaded object.

    Returns:
        str: The HTML code for the download link.
    """
    # Create a BytesIO object to hold the zip file content
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer, "a", zipfile.ZIP_DEFLATED
    ) as zip_file:
        if isinstance(object_to_download, bytes):
            # If it's already bytes (e.g., binary data), add it to the zip file
            zip_file.writestr(download_filename, object_to_download)
        else:
            # If it's not bytes, handle accordingly (modify as needed)
            raise ValueError(
                "Unsupported type for object_to_download"
            )

    # Get the BytesIO object's content as bytes
    zip_content = zip_buffer.getvalue()

    # Encode the zip content in base64
    b64 = base64.b64encode(zip_content).decode()

    # Create the download link
    dl_link = f"""
    <html>
    <head>
    <title>Start Auto Download file</title>
    <script src="https://code.jquery.com/jquery-3.2.1.min.js"></script>
    <script>
    $('<a href="data:application/zip;base64,{b64}" download="{download_filename}">')[0].click()
    </script>
    </head>
    </html>
    """
    return dl_link


def download_file():
    """Downloads the generated email files as a zip archive."""

    with st.spinner("Downloading Email files ..."):
        st.session_state.email_gen = True

        if st.session_state.draft_elements is not None:
            # Create copies to avoid modifying session data
            prod_content = st.session_state.draft_elements.copy()
            titles = st.session_state.selected_titles.copy()

            # Handle the case of multiple titles including assorted content
            if len(st.session_state.selected_titles) > 1:
                prod_content.append(
                    st.session_state.assorted_prod_content
                )
                titles.append(st.session_state.assorted_prod_title)

            # Prepare file lists for the zip file
            pdf_paths = []
            filenames = []

            # Variable to store the name of email_file
            email_file_title = st.session_state.assorted_prod_title

            for i, title in enumerate(titles):
                st.session_state.email_files = []
                generate_email(prod_content[i], title)

                # Generate a single file for each title
                pdf_path = f"./{st.session_state.email_files[0]}"
                filename = f"{st.session_state.email_files[0]}"
                pdf_paths.append(pdf_path)
                filenames.append(filename)

            # Create the zip file in memoryz
            buffer1 = io.BytesIO()
            with zipfile.ZipFile(
                buffer1, "a", zipfile.ZIP_DEFLATED
            ) as zip_file:
                for pdf_path, filename in zip(pdf_paths, filenames):
                    with open(pdf_path, "rb") as pdf_file:
                        zip_file.writestr(filename, pdf_file.read())

    # Provide download button with appropriate filename
    components.html(
        download_button(
            buffer1.getvalue(), f"email_{email_file_title}.zip"
        ),
        height=0,
    )
    st.success("Email Copies Downloaded")


def download_content():
    """Downloads the generated content as a zip archive."""

    with st.spinner("Creating Content pdf"):
        # Create copies of session data to avoid modification
        prod_content = st.session_state.draft_elements.copy()
        titles = st.session_state.selected_titles.copy()

        # Handle the case where assorted content is included
        if len(st.session_state.selected_titles) > 1:
            titles.append(st.session_state.assorted_prod_title)
            prod_content.append(
                st.session_state.assorted_prod_content
            )
        else:
            prod_content.append("")

        # Call the function to generate content PDFs
        create_content_pdf(prod_content, titles)

        # Create the zip archive
        pdf_paths = []
        filenames = []

        # Generate file paths and filenames
        for i in range(len(titles)):
            pdf_paths.append(f"./content_{i}.pdf")
            filenames.append(f"content_{i}.pdf")

        # Create an in-memory buffer for the zip file
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zip_file:
            # Write each PDF file to the zip archive
            for j, path in enumerate(pdf_paths):
                zip_file.write(path, filenames[j])

        st.session_state.buffer = buffer
        buffer1 = io.BytesIO()

        with zipfile.ZipFile(
            buffer1, "a", zipfile.ZIP_DEFLATED
        ) as zip_file:
            for pdf_path, filename in zip(pdf_paths, filenames):
                with open(pdf_path, "rb") as pdf_file:
                    zip_file.writestr(filename, pdf_file.read())

    # Prepare download button with a dynamic filename
    components.html(
        download_button(
            buffer1.getvalue(), f"content_{titles[i]}.zip"
        ),
        height=0,
    )
    st.success("Downloaded Content Zip.")
