"""
Entry page of the streamlit application.
"""

import base64

import app.pages_utils.utils as utils
from app.pages_utils.utils_config import PAGES_CFG
import app.pages_utils.utils_styles as utils_styles
from st_pages import show_pages_from_config
import streamlit as st

# Initialize session state if not already initialized
if "initialize_session_state" not in st.session_state:
    st.session_state.initialize_session_state = False

# Initialize session state if not already initialized
if st.session_state.initialize_session_state is False:
    utils.initialize_all_session_state()
    st.session_state.initialize_session_state = True

# get the page configuration for the home page
page_cfg = PAGES_CFG["home"]

# set page configuration
# page_title: The title of the page that will be displayed in the browser tab.
# page_icon: The icon that will be displayed in the browser tab.
st.set_page_config(
    page_title=page_cfg["page_title"],
    page_icon=page_cfg["page_icon"],
)

show_pages_from_config()
# sidebar_apply_style: This function applies the sidebar style to the sidebar.
# style: The style to be applied to the sidebar.
# image_path: The path to the image to be displayed on the sidebar.
utils_styles.sidebar_apply_style(
    style=utils_styles.STYLE_SIDEBAR,
    image_path=page_cfg["sidebar_image_path"],
)

file_name_1 = page_cfg["file_name_1"]
file_name_2 = page_cfg["file_name_2"]

# read the image from the file
# main_image_1: The main image to be displayed on the home page.
# main_image_2: The second main image to be displayed on the home page.
with open(file_name_1, "rb") as fp:
    contents = fp.read()
    main_image_1 = base64.b64encode(contents).decode("utf-8")
    main_image_1 = "data:image/png;base64," + main_image_1

with open(file_name_2, "rb") as fp:
    contents = fp.read()
    main_image_2 = base64.b64encode(contents).decode("utf-8")
    main_image_2 = "data:image/png;base64," + main_image_2

st.image(image=main_image_1)
st.divider()
st.image(image=main_image_2)
