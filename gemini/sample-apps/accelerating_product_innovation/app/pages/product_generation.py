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
* Export Options:  Enables downloading generated content and creating email copies.
* Image Editing:  Facilitates redirection to an image editing page.
"""

import asyncio
import logging

import base64

import app.pages_utils.utils as utils
import app.pages_utils.utils_styles as utils_styles
import app.pages_utils.utils as utils
from app.pages_utils.utils_config import PAGES_CFG
from app.pages_utils.utils_downloads import download_content, download_file
from app.pages_utils.utils_draft_generation import ProductDrafts
from app.pages_utils.utils_product_features import (
    generate_formatted_response,
    modify_selection,
    render_features,
)
from app.pages_utils.utils_product_gen import render_content, build_prompt_form, update_generation_state
import streamlit as st

# Define functions for initializing the page.
def prod_gen_styles():
    """
    This function applies custom styles to the page.

    Args:
        None

    Returns:
        None
    """
    st.markdown(
        """<style>
                div.stButton > button:first-child {
                border-radius:25px;
    }
                </style>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """<style>
        [class = "st-emotion-cache-1e9n592 ef3psqc11"] {
            border-radius: 25px !important;
        }
    </style>""",
        unsafe_allow_html=True,
    )


@st.cache_data
def get_prod_gen_img():
    """
    This function loads an image from a file and encodes it in base64 format.

    Args:
        page_cfg (dict): A dictionary containing the configuration for the page.

    Returns:
        str: The base64 encoded image.
    """
    file_name = page_cfg["prod_gen_img"]

    with open(file_name, "rb") as fp:
        contents = fp.read()
        main_image_1 = base64.b64encode(contents).decode("utf-8")
        main_image_1 = "data:image/png;base64," + main_image_1

    return main_image_1


def initialize_prod_gen():
    """
    This function initializes the session state for the product generation page.

    Args:
        None

    Returns:
        None
    """
    # Check and initialize sessions state for the project.
    if (
        "initialize_session_state" not in st.session_state
        or st.session_state.initialize_session_state is False
    ):
        utils.initialize_all_session_state()
        st.session_state.initialize_session_state = True

    st.session_state.image_file_prefix = (
        "gen_image"  # All images generated on this page have prefix 'gen_image'
    )
    st.session_state.image_to_edit = -1  # No image is being edited.
    st.session_state.text_to_edit = -1  # Text is not being edited
    st.session_state.suggested_images = (
        None  # Tracks whether image suggestions have been generated (on edit image).
    )
    st.session_state.generate_images = (
        False  # Tracks whetehr images for product ideas have been generated.
    )


def initialize_page():
    """
    This function initializes the page configuration and applies custom styles.

    Args:
        page_cfg (dict): A dictionary containing the configuration for the page.

    Returns:
        None
    """
    st.set_page_config(
        page_title=page_cfg["page_title"],
        page_icon=page_cfg["page_icon"],
    )

    utils_styles.sidebar_apply_style(
        style=utils_styles.STYLE_SIDEBAR,
        image_path=page_cfg["sidebar_image_path"],
    )
    top_img = get_prod_gen_img()
    st.image(top_img)

# Set product generation states
initialize_prod_gen()

# Initialize page config
page_cfg = PAGES_CFG["3_Generations"]
initialize_page()

# Page styles
prod_gen_styles()

# logging initialization
logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

# page title
st.write(
    "This page provides a step-by-step guide to generating products with desired characteristics."
)

# Display the project selected by the user
utils.display_projects()

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

    # Colunms for four buttons for product content
    content_gen_btns = st.columns([10, 4, 10, 4, 10, 4, 10])

    # product content container
    content = st.empty()

    # Generate Button
    with content_gen_btns[0]:
        # Get content corresponding to the features
        asyncio.run(render_content(features))

    # Display the generated content drafts
    product_drafts = ProductDrafts()
    product_drafts.display_drafts()

    if st.session_state.create_product is True:
        # Modify Button
        with content_gen_btns[2]:
            modify_btn = st.button("Modify Selection", type="primary")

        # Redisplay the product drafts if content is being modified
        if modify_btn:
            modify_selection(content)

    if st.session_state.create_product is True:
        # Email download Button
        with content_gen_btns[4]:
            email_dl_btn = st.button(
                "Generate Email Copy",
                on_click=download_file,
                type="primary",
            )

    if st.session_state.create_product is True:
        # Download Content Button
        with content_gen_btns[6]:
            if st.session_state.product_content is not None:
                export_btn = st.button(
                    "Export Content",
                    on_click=download_content,
                    type="primary",
                )

    # If user clicks edit image, redirect to edit page
    if st.session_state.image_to_edit != -1 or st.session_state.generate_images is True:
        st.switch_page("pages/edit_image.py")
