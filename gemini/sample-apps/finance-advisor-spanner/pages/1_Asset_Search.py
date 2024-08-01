"""This module is the page for Asset Search feature"""

# pylint: disable=line-too-long, invalid-name, import-error, use-dict-literal, duplicate-code, possibly-used-before-assignment

import time as t

from css import favicon, footer
from database import fts_query, like_query, display_spanner_query
from itables.streamlit import interactive_table
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


def local_css(file_name: str) -> None:
    """This loads local css"""
    with open(file_name, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


local_css("pages/styles.css")


def asset_search_precise() -> None:
    """This function implements Asset search LIKE Query"""

    st.header("FinVest Fund Advisor")
    st.subheader("Asset Search")

    st.columns([0.25, 0.25, 0.20, 0.10])
    classes = ["display", "compact", "cell-border", "stripe"]
    buttons = ["pageLength", "csvHtml5", "excelHtml5", "colvis"]
    style = "table-layout:auto;width:auto;margin:auto;caption-side:bottom"
    it_args = dict(
        classes=classes,
        style=style,
    )

    if buttons:
        it_args["buttons"] = buttons

    query_params = []
    query_params.append(investment_strategy_pt1.strip())
    query_params.append(and_or_exclude)
    query_params.append(investment_strategy_pt2.strip())
    query_params.append(investment_manager.strip())

    with st.spinner("Querying Spanner..."):
        t.sleep(1)

        return_vals = like_query(query_params)
        spanner_query = return_vals.get("query")
        data = return_vals.get("data")
        display_spanner_query(spanner_query)

    interactive_table(data, caption="", **it_args)


def asset_search() -> None:
    """This function immplements Asset Search"""

    st.header("FinVest Fund Advisor")
    st.subheader("Asset Search")

    st.columns([0.25, 0.25, 0.20, 0.10])
    classes = ["display", "compact", "cell-border", "stripe"]
    buttons = ["pageLength", "csvHtml5", "excelHtml5", "colvis"]
    style = "table-layout:auto;width:auto;margin:auto;caption-side:bottom"
    it_args = dict(
        classes=classes,
        style=style,
    )

    if buttons:
        it_args["buttons"] = buttons

    query_params = []
    query_params.append(investment_strategy)
    query_params.append(investment_manager)

    with st.spinner("Querying Spanner..."):
        t.sleep(1)

        return_vals = fts_query(query_params)
        spanner_query = return_vals.get("query")
        data = return_vals.get("data")

        display_spanner_query(spanner_query)

    interactive_table(data, caption="", **it_args)


with st.sidebar:
    with st.form("Asset Search"):
        st.subheader("Search Criteria")
        precise_vs_text = st.radio("", ["Full-Text", "Precise"], horizontal=True)
        precise_search = False
        with st.expander("Asset Strategy", expanded=True):
            investment_strategy_pt1 = st.text_input("", value="Europe")
            and_or_exclude = st.radio("", ["AND", "OR", "EXCLUDE"], horizontal=True)
            investment_strategy_pt2 = st.text_input("", value="Asia")
        investment_manager = st.text_input("Investment Manager", value="James")
        if precise_vs_text == "Full-Text":
            if and_or_exclude == "EXCLUDE":
                investment_strategy = (
                    investment_strategy_pt1 + " -" + investment_strategy_pt2
                )
            else:
                investment_strategy = (
                    investment_strategy_pt1
                    + " "
                    + and_or_exclude
                    + " "
                    + investment_strategy_pt2
                )
        else:
            precise_search = True
        asset_search_submitted = st.form_submit_button("Submit")
if asset_search_submitted:
    if precise_search:
        asset_search_precise()
    else:
        asset_search()

st.markdown(footer, unsafe_allow_html=True)
