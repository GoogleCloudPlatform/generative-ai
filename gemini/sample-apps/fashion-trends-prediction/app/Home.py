import streamlit as st
from config import config
from utilities import add_logo, render_svg

PROJECT_ID = config["PROJECT_ID"]  # @param {type:"string"}
LOCATION = config["LOCATION"]  # @param {type:"string"}


st.set_page_config(
    page_title="Fashion Trend",
)
add_logo(config["Images"]["logo"])


# Set the path to the local image file
image_path1 = config["Images"]["slide1"]
image_path2 = config["Images"]["slide2"]


# Read the SVG image as a string
with open(image_path1, "r") as f:
    svg1 = f.read()
with open(image_path2, "r") as f:
    svg2 = f.read()


render_svg(svg1)
st.markdown(
    """<hr style="height:1px;border:none;color:#333;background-color:#333;" /> """,
    unsafe_allow_html=True,
)
render_svg(svg2)
