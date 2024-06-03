"""
This module provides functions for image processing and session state
management
related to image editing.  This module:
* process_foreground_image():
    * Prepares a foreground image for merging with a background.
    * Optionally removes white regions for background editing.
* initialize_edit_page_state():  Initializes session state for the
  image editing
page and handles uploaded images.
* handle_image_upload(): Manages the image upload process and updates session
 state.
* save_draft_image(): Saves edited draft images and facilitates a return to
 the product
generation page.
* generate_suggested_images():
    * Generates image variations based on text prompts, an initial image, and
      an optional mask.
* render_suggested_images():
    * Displays generated suggestions in a grid.
    * Provides "Edit" and "Download" buttons for each suggestion.
* _handle_edit_suggestion():
    * Handles the logic for editing a selected suggestion.
"""

import io
import logging

import PIL
from PIL import Image
from app.pages_utils.imagen import predict_edit_image
import streamlit as st
from vertexai.preview.vision_models import Image as vertex_image

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)


def process_foreground_image(
    foreground_image: Image.Image,
    background_image: Image.Image,
    bg_editing: bool = False,
) -> bytes:
    """
    Processes a foreground image, optionally removing white regions,
    and prepares it for merging with a background image.

    Args:
        foreground_image (Image.Image): The PIL Image object representing the
        foreground.
        background_image (Image.Image): The PIL Image object representing the
        background.
        bg_editing (bool, optional): If True, removes white regions from the
        foreground. Defaults to False.

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
                new_bytes.append((255, 255, 255, 1))

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


def initialize_edit_page_state() -> None:
    """
    Initializes the session state for the image editing page.

    This function checks if the session state has been initialized, and if not,
    it initializes it.
    It also checks if an image has been uploaded, and if so, it sets
    the session state accordingly.
    """

    # Check which image file prefix points to the image to be edited
    if "image_to_edit" not in st.session_state or st.session_state.image_to_edit == -1:
        st.session_state.image_to_edit = (
            -1
        )  # No image from generations is being edited.
        st.session_state.image_file_prefix = (
            "uploaded_image"  # image prefix for editing uploaded image.
        )
        st.session_state.uploaded_img = True  # Set image uploaded to true.
    else:
        st.session_state.uploaded_img = False  # Generated image being edited.
        st.session_state.start_editing = True  # Display canvas for editing.


def handle_image_upload() -> None:
    """
    Handles an image upload, saving the image and updating session state.
    """
    # Upload button
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


def save_draft_image(
    row: int, col: int, image: Image.Image, draft_elements: dict
) -> None:
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
    image.save(f"gen_image{image_num}.png")

    # Display the edited image on product generation image
    st.switch_page("pages/product_generation.py")


def render_suggested_images(suggested_images: list[str]) -> None:
    """
    Renders suggested images in a grid layout with "Edit" and "Download"
    buttons.

    Args:
        suggested_images: A list of image paths or data to display as
        suggestions.
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
                image_data = suggested_images[image_index]
                st.download_button(
                    label="Download",
                    data=image_data,
                    file_name=f"suggestion_{image_index}.png",
                    mime="image/png",
                    type="primary",
                )


def _handle_edit_suggestion(image_index: int) -> None:
    """Handles the logic for when the 'Edit' button is clicked.
    Args:
        image_index (int): corresponding draft number of image being edited.
    """
    # Get Byte data of the image.
    image_data = io.BytesIO(st.session_state.suggested_images[image_index])
    # Save image.
    with open("suggestion1.png", "wb") as f:
        f.write(image_data.getvalue())

    # Update state.
    st.session_state.edit_suggestion = (
        True  # Track whether a suggestion is being edited.
    )
    st.session_state.image_file_prefix = (
        "suggestion"  # Image saved with prefix suggestion is being edited.
    )
    st.session_state.image_to_edit = 0  # Track which image is being edited
    st.session_state.mask_image = None  # Reset Mask
    st.rerun()


def save_image_for_editing(image_bytes: bytes, filename: str) -> None:
    """
    Saves image for image editing by Imagen

    Args:
        image_bytes (bytes): Image bytes for the image to saved.
        filename (str): Name of the saved file.
    """
    # Create a BytesIO object from the image bytes
    image_stream = io.BytesIO(image_bytes)

    # Open the image using Pillow
    image = Image.open(image_stream)

    # Save the image as a PNG
    image.save(f"{filename}.png", "PNG")


def generate_suggested_images(
    image_prompt: str,
    image_bytes: io.BytesIO,
    mask_image: bytes,
    sample_count: int = 6,
) -> None:
    """
    Generates suggested images based on the provided prompt, image, and mask.
    Updates Streamlit session state with the generated images.

    Args:
        image_prompt (str): Text prompt for image generation.
        image_bytes (BytesIO): Initial image data for editing.
        mask_image (bytes): Mask defining the region to
        edit (optional).
    """
    save_image_for_editing(image_bytes.getvalue(), "image_to_edit")
    save_image_for_editing(mask_image, "mask")

    st.session_state.suggested_images = []  # Clear previous suggestions

    # Generated edit image results
    with st.spinner("Generating suggested images"):
        input_dict = {
            "prompt": image_prompt,
            "image": vertex_image.load_from_file("image_to_edit.png"),
        }

        if mask_image:
            input_dict["mask"] = vertex_image.load_from_file("mask.png")

        st.session_state["generated_image"] = predict_edit_image(
            instance_dict=input_dict,
            parameters={"sampleCount": sample_count},
        )

    # Append newly generated suggestions to suggested images state key.
    for image_data in st.session_state.generated_image:
        st.session_state.suggested_images.append(image_data.__dict__["_loaded_bytes"])
    # End image generation.
    st.session_state.generate_images = False  # Update generation state
