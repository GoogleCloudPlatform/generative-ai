"""This module is the page for Exposure Check Search feature"""

# pylint: disable=line-too-long,import-error,invalid-name

from database import compliance_query, display_spanner_query
from home import table_columns_layout_setup
from itables.streamlit import interactive_table
import streamlit as st

st.logo(
    "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/investments.png"
)


def compliance_search() -> None:
    """This function implements Compliance Check Graph feature"""
    st.header("FinVest Fund Advisor")
    st.subheader("Exposure Check")

    query_params = []
    query_params.append(sectorOption)
    query_params.append(exposurePercentage)
    with st.spinner("Querying Spanner..."):
        compliance_vals = compliance_query(query_params)
        compliance_queries = compliance_vals.get("query")
        data = compliance_vals.get("data")
        display_spanner_query(str(compliance_queries))

    interactive_table(data, caption="", **table_columns_layout_setup())


with st.sidebar:
    with st.form("Compliance Search"):
        st.subheader("Search Criteria")
        sectorOption = st.selectbox(
            "Which sector would you want to focus on?",
            ("Technology", "Pharma", "Semiconductors"),
            index=None,
            placeholder="Select sector ...",
        )
        exposurePercentage = st.select_slider(
            "How much exposure to this sector would you prefer",
            options=["10%", "20%", "30%", "40%", "50%", "60%", "70%"],
        )
        exposurePercentage = exposurePercentage[:2]
        compliance_search_submitted = st.form_submit_button("Submit")
if compliance_search_submitted:
    compliance_search()
