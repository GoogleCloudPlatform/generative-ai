"""This module is the page for Asset Search feature"""

# pylint: disable=line-too-long,import-error,invalid-name

from database import display_spanner_query, fts_query, like_query
from home import table_columns_layout_setup
from itables.streamlit import interactive_table
import streamlit as st

st.logo(
    "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/investments.png"
)


def asset_search_common(query_parameters: list, query_type: str) -> None:
    """This function implements Asset search common  functions"""

    st.header("FinVest Fund Advisor")
    st.subheader("Asset Search")

    with st.spinner("Querying Spanner..."):
        if query_type == "PRECISE":
            return_vals = like_query(query_parameters)
        else:
            return_vals = fts_query(query_parameters)
        spanner_query = return_vals.get("query")
        data = return_vals.get("data")
        display_spanner_query(str(spanner_query))

    interactive_table(data, caption="", **table_columns_layout_setup())


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
        investment_strategy = ""
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
        query_params = [
            investment_strategy_pt1.strip(),
            and_or_exclude,
            investment_strategy_pt2.strip(),
            investment_manager.strip(),
        ]
        asset_search_common(query_params, "PRECISE")
    else:
        query_params = [investment_strategy, investment_manager]
        asset_search_common(query_params, "FTS")
