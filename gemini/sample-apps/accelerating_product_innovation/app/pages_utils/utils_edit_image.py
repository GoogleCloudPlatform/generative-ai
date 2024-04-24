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
* generate_suggested_images():
    * Generates image variations based on text prompts, an initial image, and an optional mask.
* render_suggested_images():
    * Displays generated suggestions in a grid.
    * Provides "Edit" and "Download" buttons for each suggestion.
* _handle_edit_suggestion():
    * Handles the logic for editing a selected suggestion.
"""

import base64
import io
import logging

import PIL
from PIL import Image
from app.pages_utils.utils_imagen import edit_image_generation

import streamlit as st

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)


def process_foreground_image(foreground_image, background_image, bg_editing=False):
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
    resized_foreground = foreground_image.resize(background_image.size)
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

    # Check which image file prefix points to the image to be edited
    if "image_to_edit" not in st.session_state or st.session_state.image_to_edit == -1:
        st.session_state.image_to_edit = (
            -1
        )  # No image from generations is being edited.
        st.session_state.image_file_prefix = (
            "./uploaded_image"  # image prefix for editing uploaded image.
        )
        st.session_state.uploaded_img = True  # Set image uploaded to true.
    else:
        st.session_state.uploaded_img = False  # Generated image being edited.
        st.session_state.start_editing = True  # Display canvas for editing.


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

    st.session_state.content_edited = True  # Track whether image has been edited.
    draft_elements[row][col][
        "img"
    ] = image  # Update the drafts to display updated image.

    # Calculate unique image filename and save image.
    image_num = st.session_state.num_drafts * row + col + 1
    image.save(f"./gen_image{image_num}.png")

    # Display the edited image on product generation image
    st.switch_page("pages/product_generation.py")


def download_image(image_data, image_name):
    """
    Creates download button for given image.

    Args:
        image_data: Byte data of the image to be downloaded.
        image_name: Name of the image file.
    """
    st.download_button(
        label="Download",
        data=image_data,
        file_name=image_name,
        mime="image/png",
        type="primary",
    )


def render_suggested_images(suggested_images, generated_images):
    """
    Renders suggested images in a grid layout with "Edit" and "Download" buttons.

    Args:
        suggested_images: A list of image paths or data to display as suggestions.
        generated_images: A list of dictionaries containing base64-encoded image data
                          with keys like 'bytesBase64Encoded'
    """

    # Set number of images to be displayed per row.
    num_suggestions_per_row = 3

    # Iterate over image rows.
    for row_start in range(0, len(suggested_images), num_suggestions_per_row):
        # Create columns to display each image.
        suggestion_cols = st.columns(num_suggestions_per_row)
        for col_index, col in enumerate(suggestion_cols):
            # Calculate image index
            image_index = row_start + col_index
            with col:
                # Display image.
                st.image(suggested_images[image_index])
                # Add Edit image button for the current suggestion.
                if st.button(
                    "Edit",
                    key=f"edit suggestion {image_index}",
                    type="primary",
                ):
                    _handle_edit_suggestion(image_index)
                # Add download button for current suggestion.
                image_data = io.BytesIO(
                    base64.b64decode(
                        generated_images[image_index]["bytesBase64Encoded"]
                    )
                )
                download_image(image_data, f"suggestion_{image_index}.png")


def _handle_edit_suggestion(image_index):
    """Handles the logic for when the 'Edit' button is clicked."""
    # Get Byte data of the image.
    image_data = io.BytesIO(
        base64.b64decode(
            st.session_state.generated_image[image_index]["bytesBase64Encoded"]
        )
    )
    # Save image.
    with open("./suggestion1.png", "wb") as f:
        f.write(image_data.getvalue())

    # Update state.
    st.session_state.edit_suggestion = (
        True  # Track whether a suggestion is being edited.
    )
    st.session_state.image_file_prefix = (
        "suggestion"  # Image saved with prefix suggestion is beig edited.
    )
    st.session_state.image_to_edit = 0  # Track which image is being edited
    st.session_state.mask_image = None  # Reset Mask
    st.rerun()


def generate_suggested_images(image_prompt, image_bytes, mask_image):
    """
    Generates suggested images based on the provided prompt, image, and mask.
    Updates Streamlit session state with the generated images.

    Args:
        image_prompt (str): Text prompt for image generation.
        image_bytes (BytesIO): Initial image data for inpainting or variation.
        mask_image (BytesIO or None): Mask defining the region to edit (optional).
    """

    st.session_state.suggested_images = []  # Clear previous suggestions
    with st.spinner("Generating suggested images"):
        edit_image_completed = edit_image_generation(
            image_prompt,
            6,  # Number of suggested images to be generated
            image_bytes.getvalue(),
            "generated_image",  # Session state key for storing results
            mask_image,  # Mask value
        )

    # Append newly generated suggestions to suggested images state key.
    if edit_image_completed:
        for image_data in st.session_state.generated_image:
            encoded_image = base64.b64decode(image_data["bytesBase64Encoded"])
            st.session_state.suggested_images.append(io.BytesIO(encoded_image))
    else:
        st.session_state.suggested_images = None
    # End image generation.
    st.session_state.generate_images = False  # Update generation state
