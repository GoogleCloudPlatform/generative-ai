"""This file is the home Page of the Python Streamlit app"""

# pylint: disable= import-error,line-too-long

import streamlit as st

st.set_page_config(
    layout="wide",
    page_title="FinVest Advisor",
    page_icon="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/small-logo.png",
    initial_sidebar_state="expanded",
)


st.logo(
    "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/investments.png"
)

st.header("Welcome")
st.image(
    "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/Finvest-white-removebg-preview.png"
)

