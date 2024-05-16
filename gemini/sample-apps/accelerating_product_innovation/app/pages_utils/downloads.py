"""
This module provides functions for downloading generated content (emails,
product content)
as zip archives.
"""

import base64
import io
import logging
from typing import Any
import zipfile

from app.pages_utils.export_content_pdf import create_content_pdf, create_email_pdf
from app.pages_utils.get_llm_response import generate_gemini
from app.pages_utils.imagen import image_generation
from dotenv import load_dotenv
import streamlit as st
import streamlit.components.v1 as components

load_dotenv()

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
st.session_state.image_file_prefix = "email_image"


def generate_email(prompt: str, title: str) -> None:
    """Generates an email PDF with the given prompt and title.

    Args:
        prompt (str): The prompt for the email text.
        title (str): The title of the email.
    """
    # Create prompt for email generation for given product idea.
    email_prompt = f"""Write an email introducing the concept for a new
    product, {prompt}. Write the benefits for different demographics,
    skin types, genders, etc., too.
    The email should strictly share the concept with the innovation team.
    The email should strictly not announce launch, only the concept.
    Keep the email brief."""

    # Generate Email content.
    email_text = generate_gemini(email_prompt)
    st.session_state.email_text = email_text  # update state.

    # Generate corresponding image for email copy.
    image_generation(
        f"""Generate a beautiful image of a {st.session_state.product_category}
        in an aesthetic background. Image should be suitable for advertising.
        Content should be written on packaging in English.""",
        1,
        "1:1",
        "email_image",
    )

    # Generate pdf containing the email content and image.
    create_email_pdf(
        title,
        email_text.replace("**", ""),
        f"email_copy_0_{title}",
        "email_image.png",
    )
    st.session_state.email_files.append(f"email_copy_0_{title}.pdf")


def download_button(object_to_download: bytes, download_filename: str) -> str:
    """Generates a download link for the given object.

    Args:
        object_to_download (bytes or str): The object to download.
        download_filename (str): The filename of the downloaded object.

    Returns:
        str: The HTML code for the download link.
    """
    # Create a BytesIO object to hold the zip file content
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
        if isinstance(object_to_download, bytes):
            # If it's already bytes (e.g., binary data), add it to the zip file
            zip_file.writestr(download_filename, object_to_download)
        else:
            # If it's not bytes, handle accordingly (modify as needed)
            raise ValueError("Unsupported type for object_to_download")

    # Get the BytesIO object's content as bytes
    zip_content = zip_buffer.getvalue()

    # Encode the zip content in base64
    b64 = base64.b64encode(zip_content).decode()

    # Read the HTML template file
    with open("app/download_link.html", "r", encoding="utf8") as f:
        html_template = f.read()

    # Replace placeholders in the HTML template
    html_link = html_template.replace("{b64}", b64)
    html_link = html_link.replace("{download_filename}", download_filename)

    return html_link


def create_zip_buffer(filenames: list[str]) -> io.BytesIO:
    """Creates a BytesIO object containing a zip file of the specified files.

    Args:
        filenames: A list of filenames to include in the zip archive.

    Returns:
        An io.BytesIO object representing the zip file in memory.
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
        for filename in filenames:
            with open(f"./{filename}", "rb") as pdf_file:
                zip_file.writestr(filename, pdf_file.read())
    return zip_buffer


def load_product_lists() -> tuple[list[list[dict[str, Any]]], list[str]]:
    """
    Creates copies of Product titles and content to be imported.
    Returns:
        Tuple containing two lists - Product Content and titles.
    """
    # Create copies to avoid modifying session data
    prod_content = st.session_state.draft_elements.copy()
    titles = st.session_state.selected_titles.copy()

    # Handle the case of multiple titles including assorted content
    if len(st.session_state.selected_titles) > 1:
        prod_content.append(st.session_state.assorted_prod_content)
        titles.append(st.session_state.assorted_prod_title)
    else:
        prod_content.append("")

    return prod_content, titles


def download_file() -> None:
    """Downloads the generated email files as a zip archive."""

    with st.spinner("Downloading Email files ..."):
        st.session_state.email_gen = True

        if st.session_state.draft_elements is not None:
            prod_content, titles = load_product_lists()
            # Prepare file list for the zip file
            filenames = []

            # Variable to store the name of email_file
            email_file_title = st.session_state.assorted_prod_title

            # Logic to generate content for email files.
            for i, title in enumerate(titles):
                st.session_state.email_files = []
                if st.session_state.email_gen:
                    generate_email(prod_content[i][0]["text"], title)

                # Generate a single file for each title
                filename = f"{st.session_state.email_files[0]}"
                filenames.append(filename)

            # Create the zip file in memory.
            zip_buffer = create_zip_buffer(filenames)

    # Provide download button with appropriate filename
    components.html(
        download_button(zip_buffer.getvalue(), f"email_{email_file_title}.zip"),
        height=0,
    )
    st.success("Email Copies Downloaded")


def download_content() -> None:
    """Downloads the generated content as a zip archive."""

    with st.spinner("Creating Content pdf"):
        prod_content, titles = load_product_lists()

        # Call the function to generate content PDFs
        create_content_pdf(prod_content, titles)

        # Create the zip archive
        filenames = []

        # Generate filenames
        for i in range(len(titles)):
            filenames.append(f"content_{i}.pdf")

    zip_buffer = create_zip_buffer(filenames)

    # Prepare download button with a dynamic filename
    components.html(
        download_button(zip_buffer.getvalue(), f"content_{titles[i]}.zip"),
        height=0,
    )
    st.success("Downloaded Content Zip.")
