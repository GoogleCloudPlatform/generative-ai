"""This file is the home Page of the Python Streamlit app"""

# pylint: disable= import-error,line-too-long

from css import favicon, footer
import streamlit as st

st.set_page_config(
    layout="wide",
    page_title="FinVest Advisor",
    page_icon=favicon,
    initial_sidebar_state="expanded",
)


st.logo(
    "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/investments.png"
)

st.header("Welcome")
st.image(
    "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/Finvest-white-removebg-preview.png"
)

st.markdown(footer, unsafe_allow_html=True)


def local_css(file_name: str) -> None:
    """This function loads local CSS File"""

    with open(file_name, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


local_css("pages/styles.css")
