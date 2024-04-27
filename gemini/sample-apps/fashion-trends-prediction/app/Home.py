from config import config
import streamlit as st
from utilities import add_logo, render_svg

PROJECT_ID = config["PROJECT_ID"]  # @param {type:"string"}
LOCATION = config["LOCATION"]  # @param {type:"string"}


st.set_page_config(
    page_title="Fashion Trend",
)
add_logo(config["Images"]["logo"])


render_svg(config["Images"]["slide1"])
st.markdown(
    """<hr style="height:1px;border:none;color:#333;background-color:#333;" /> """,
    unsafe_allow_html=True,
)
render_svg(config["Images"]["slide2"])
