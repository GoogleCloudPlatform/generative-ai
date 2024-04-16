"""
This module provides functions for image processing and session state management
related to image editing.  This module:
* process_foreground_image():
    * Prepares a foreground image for merging with a background.
    * Optionally removes white regions for background editing.
* initialize_edit_page_state():  Initializes session state for the image editing
page and handles uploaded images.
* handle_image_upload(): Manages the image upload process and updates session state.
* save_draft_image(): Saves edited draft images and facilitates a return to the product
generation page.
"""

import io
import logging

import PIL
import streamlit as st
from PIL import Image

import app.pages_utils.utils as utils

logging.basicConfig(
    format="%(levelname)s:%(message)s", level=logging.DEBUG
)


def process_foreground_image(
    foreground_image, background_image, bg_editing=False
):
    """
    Processes a foreground image, optionally removing white regions,
    and prepares it for merging with a background image.

    Args:
        foreground_image (Image.Image): The PIL Image object representing the foreground.
        background_image (Image.Image): The PIL Image object representing the background.
        bg_editing (bool, optional): If True, removes white regions from the foreground.
                                     Defaults to False.

    Returns:
        bytes: The processed and merged image data as bytes.
    """

    # Logic to edit background (invert mask)
    if bg_editing:
        # Get image foreground
        foreground_data = foreground_image.getdata()
        new_bytes = []
        # Invert pixels.
        for item in foreground_data:
            if item[0] == 255 and item[1] == 255 and item[2] == 255:
                new_bytes.append((255, 255, 255, 0))
            else:
                new_bytes.append((255, 255, 255))

        foreground_image.putdata(new_bytes)

    # Resize and merge foreground with background
    resized_foreground = foreground_image.resize(
        background_image.size
    )
    merged_image = background_image.copy()
    merged_image.paste(resized_foreground, (0, 0), resized_foreground)

    # Convert to bytes for storage
    with io.BytesIO() as buffer:
        merged_image.save(buffer, format="PNG")
        processed_image_bytes = buffer.getvalue()

    return processed_image_bytes


def initialize_edit_page_state():
    """
    Initializes the session state for the image editing page.

    This function checks if the session state has been initialized, and if not, it initializes it.
    It also checks if an image has been uploaded, and if so, it sets the session state accordingly.
    """

    # Initialize session state for the project if it does not exist.
    if (
        "initialize_session_state" not in st.session_state
        or st.session_state.initialize_session_state is False
    ):
        utils.initialize_all_session_state()
        st.session_state.initialize_session_state = True

    # Check which image file prefix points to the image to be edited
    if (
        "image_to_edit" not in st.session_state
        or st.session_state.image_to_edit == -1
    ):
        st.session_state.image_to_edit = (
            -1
        )  # No image from generations is being edited.
        st.session_state.image_file_prefix = "./uploaded_image"  # image prefix for editing uploaded image.
        st.session_state.uploaded_img = (
            True  # Set image uploaded to true.
        )
    else:
        st.session_state.uploaded_img = (
            False  # Generated image being edited.
        )
        st.session_state.start_editing = (
            True  # Display canvas for editing.
        )


def handle_image_upload():
    """
    Handles an image upload, saving the image and updating session state.
    """
    # Uplad button
    uploaded_file = st.file_uploader("Upload an image")

    # If image has been uploaded open and Save uploaded image.
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            filename = "uploaded_image0.png"
            image.save(filename)
            st.session_state.start_editing = True
        except (IOError, PIL.UnidentifiedImageError) as e:
            st.error(f"Error opening image: {e}")


def save_draft_image(row, col, image, draft_elements):
    """Saves the draft image and updates session state for content editing.

    Args:
        row (int): Row index of the image being edited.
        col (int): Column index of the image being edited.
        image (Image): The image object to be saved.
        draft_elements (dict): Dictionary holding the draft image elements.
    """

    st.session_state.content_edited = (
        True  # Track whether image has been edited.
    )
    draft_elements[row][col][
        "img"
    ] = image  # Update the drafts to display updated image.

    # Calculate unique image filename and save image.
    image_num = st.session_state.num_drafts * row + col + 1
    image.save(f"./gen_image{image_num}.png")

    # Display the edited image on product generation image
    st.switch_page("pages/product_generation.py")
