from config import config
import streamlit as st
from utilities import add_logo, render_svg

PROJECT_ID = config["PROJECT_ID"]  # @param {type:"string"}
LOCATION = config["LOCATION"]  # @param {type:"string"}


st.set_page_config(
    page_title="Fashion Trend",
)
add_logo(config["Images"]["logo"])


# Set the path to the local image file
slide1_image_path = config["Images"]["slide1"]
slide2_image_path = config["Images"]["slide2"]


# Read the SVG image as a string
with open(slide1_image_path, "r") as f:
    svg1 = f.read()
with open(slide2_image_path, "r") as f:
    svg2 = f.read()


render_svg(svg1)
st.markdown(
    """<hr style="height:1px;border:none;color:#333;background-color:#333;" /> """,
    unsafe_allow_html=True,
)
render_svg(svg2)
