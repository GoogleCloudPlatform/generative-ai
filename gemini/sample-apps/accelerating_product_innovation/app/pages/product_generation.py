"""
This module manages the 'Generations' page in the Streamlit application,
with a focus on guiding users through product generation. This module:

* Project Management: Displays the project selected by the user.
* Prompt-Based Generation:
   * Provides a form for users to specify product characteristics.
   * Generates product features based on the provided input.
* Content Drafts:
   * Creates and displays new product ideas based on generated features.
   * Allows users to modify their selected features and content drafts.
* Export Options:  Enables downloading generated content and creating email
  copies.
* Image Editing:  Facilitates redirection to an image editing page.
"""

import asyncio
import logging

from app.pages_utils import setup
from app.pages_utils.downloads import download_content, download_file
from app.pages_utils.draft_generation import ProductDrafts
from app.pages_utils.pages_config import PAGES_CFG
from app.pages_utils.product_features import (
    generate_formatted_response,
    modify_selection,
    render_features,
)
from app.pages_utils.product_gen import (
    build_prompt_form,
    handle_content_generation,
    update_generation_state,
)
import streamlit as st


@st.cache_data
def get_prod_gen_img() -> None:
    """
    This function loads an image from a file, displays, and caches it.

    Returns:
       None
    """
    # Display the top image for this page.
    page_images = [page_cfg["prod_gen_img"]]
    for page_image in page_images:
        st.image(page_image)


def initialize_prod_gen() -> None:
    """
    This function initializes the session state for the product generation
    page.

    Args:
        None

    Returns:
        None
    """
    # All images generated on this page have prefix 'gen_image'
    st.session_state.image_file_prefix = "gen_image"
    st.session_state.image_to_edit = -1  # No image is being edited.
    st.session_state.text_to_edit = -1  # Text is not being edited
    # Tracks whether image suggestions have been generated (on edit image).
    st.session_state.suggested_images = None
    st.session_state.generate_images = (
        False  # Tracks whether images for product ideas have been generated.
    )
    # Display header images
    get_prod_gen_img()


# Initialize page config.
page_cfg = PAGES_CFG["3_Generations"]

setup.page_setup(page_cfg)

# Set product generation states.
initialize_prod_gen()

# Page styles
setup.load_css("app/css/prod_gen_styles.css")
# logging initialization
logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

# page title
st.write(
    """This page provides a step-by-step guide to generating products with
    desired characteristics."""
)

# Display the project selected by the user
setup.display_projects()

# Product generate form
generate_btn = build_prompt_form()
if generate_btn:
    update_generation_state()

# After form submission, generate product features
if st.session_state.features_generated is True:
    if st.session_state.generated_response is None:
        st.session_state.generated_response = generate_formatted_response(
            st.session_state.selected_prompt
        )
        st.session_state.generated_points = None

# feature container
features = st.empty()
# Generated features to be displayed only if product content is not generated
if (
    st.session_state.generated_response is not None
    and st.session_state.features_generated is True
):
    if st.session_state.content_generated is False:
        # Display features on ui
        render_features(features)

    # Columns for four buttons for product content
    content_gen_buttons = st.columns([10, 4, 10, 4, 10, 4, 10])

    # product content container
    content = st.empty()

    # Generate Button
    with content_gen_buttons[0]:
        # Get content corresponding to the features
        if st.button("Generate Content", type="primary"):
            asyncio.run(handle_content_generation(features))

    # Display the generated content drafts
    product_drafts = ProductDrafts()
    product_drafts.display_drafts()

    if st.session_state.create_product is True:
        # Modify Button
        with content_gen_buttons[2]:
            modify_btn = st.button("Modify Selection", type="primary")

        # Redisplay the product drafts if content is being modified
        if modify_btn:
            modify_selection(content)

        # Email download Button
        with content_gen_buttons[4]:
            email_dl_btn = st.button(
                "Generate Email Copy",
                on_click=download_file,
                type="primary",
            )

        # Download Content Button
        with content_gen_buttons[6]:
            if st.session_state.product_content is not None:
                export_btn = st.button(
                    "Export Content",
                    on_click=download_content,
                    type="primary",
                )

    # If user clicks edit image, redirect to edit page
    if st.session_state.image_to_edit != -1 or st.session_state.generate_images is True:
        st.switch_page("pages/edit_image.py")
