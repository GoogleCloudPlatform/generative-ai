"""
This module provides functions for initializing and customizing 
the appearance of the product generation page.
"""

import base64

import streamlit as st
import app.pages_utils.utils as utils

import app.pages_utils.utils_styles as utils_styles


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
def get_prod_gen_img(page_cfg):
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

    st.session_state.image_file_prefix = "gen_image"  # All images generated on this page have prefix 'gen_image'
    st.session_state.image_to_edit = -1  # No image is being edited.
    st.session_state.text_to_edit = -1  # Text is not being edited
    st.session_state.suggested_images = None  # Tracks whether image suggestions have been generated (on edit image).
    st.session_state.generate_images = False  # Tracks whetehr images for product ideas have been generated.


def initialize_page(page_cfg):
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
    top_img = get_prod_gen_img(page_cfg)
    st.image(top_img)
