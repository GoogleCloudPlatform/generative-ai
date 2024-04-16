"""
This module provides functions for generating and interacting with image suggestions
during the editing process. This module:

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

from app.pages_utils.utils_imagen import edit_image_generation
import streamlit as st

logging.basicConfig(
    format="%(levelname)s:%(message)s", level=logging.DEBUG
)


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
    for row_start in range(
        0, len(suggested_images), num_suggestions_per_row
    ):
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
                        generated_images[image_index][
                            "bytesBase64Encoded"
                        ]
                    )
                )
                download_image(
                    image_data, f"suggestion_{image_index}.png"
                )


def _handle_edit_suggestion(image_index):
    """Handles the logic for when the 'Edit' button is clicked."""
    # Get Byte data of the image.
    image_data = io.BytesIO(
        base64.b64decode(
            st.session_state.generated_image[image_index][
                "bytesBase64Encoded"
            ]
        )
    )
    # Save image.
    with open("./suggestion1.png", "wb") as f:
        f.write(image_data.getvalue())

    # Update state.
    st.session_state.edit_suggestion = (
        True  # Track whether a suggestion is being edited.
    )
    st.session_state.image_file_prefix = "suggestion"  # Image saved with prefix suggestion is beig edited.
    st.session_state.image_to_edit = (
        0  # Track which image is being edited
    )
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

    st.session_state.suggested_images = (
        []
    )  # Clear previous suggestions
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
            encoded_image = base64.b64decode(
                image_data["bytesBase64Encoded"]
            )
            st.session_state.suggested_images.append(
                io.BytesIO(encoded_image)
            )
    else:
        st.session_state.suggested_images = None
    # End image generation.
    st.session_state.generate_images = (
        False  # Update generation state
    )
