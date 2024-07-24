"""This file is the home Page of the Python Streamlit app"""

import streamlit as st
from database import *
from css import *

st.set_page_config(
    layout="wide",
    page_title="FinVest Advisor",
    page_icon=favicon,
    initial_sidebar_state="expanded",
)


st.logo("images/investments.png")

st.header("Welcome")
# st.image('images/investments.png')
st.image("images/Finvest-white-removebg-preview.png")

st.markdown(footer, unsafe_allow_html=True)


def local_css(file_name):
    """This function loads local CSS File"""

    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


local_css("pages/styles.css")
