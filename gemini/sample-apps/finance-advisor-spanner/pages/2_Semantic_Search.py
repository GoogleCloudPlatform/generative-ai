"""This module is the page for Semantic Search feature"""

# pylint: disable=line-too-long,import-error,invalid-name

from database import display_spanner_query, semantic_query, semantic_query_ann
from home import table_columns_layout_setup
from itables.streamlit import interactive_table
import streamlit as st

st.logo(
    "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/investments.png"
)


def asset_semantic_search() -> None:
    """This function implements Semantic Search feature"""

    st.header("FinVest Fund Advisor")
    st.subheader("Semantic Search")
    query_params = [investment_strategy.strip(), investment_manager.strip()]

    with st.spinner("Querying Spanner..."):
        if annVsKNN == "KNN":
            semantic_return_vals = semantic_query(query_params)
        else:
            semantic_return_vals = semantic_query_ann(query_params)
        semantic_queries = semantic_return_vals.get("query")
        data = semantic_return_vals.get("data")
        display_spanner_query(str(semantic_queries))

    interactive_table(data, caption="", **table_columns_layout_setup())


with st.sidebar:
    with st.form("Asset Semantic Search"):
        st.subheader("Search Criteria")
        annVsKNN = st.radio("", ["ANN", "KNN"], horizontal=True)
        investment_strategy = st.text_area(
            "Search for me",
            value="Invest in companies which also subscribe to my ideas around climate change, doing good for the planet",
        )
        investment_manager = st.text_input("Investment Manager", value="Maarten")
        asset_semantic_search_submitted = st.form_submit_button("Submit")
if asset_semantic_search_submitted:
    asset_semantic_search()
