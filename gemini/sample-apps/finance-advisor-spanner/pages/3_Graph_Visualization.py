"""This module is the page for Graph Visualization feature"""

# pylint: disable=line-too-long,import-error,invalid-name

import graph_viz
import streamlit as st
import streamlit.components.v1 as components

st.subheader("Show me the Relationships between Funds ,Companies and Sectors")

st.logo(
    "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/investments.png"
)
graph_viz.generate_graph()

with open("graph_viz.html", encoding="utf-8") as html_file:
    source_code = html_file.read()
components.html(source_code, height=950, width=900)

with st.sidebar:
    st.subheader("Legend")
    st.image(
        "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/Graph-legend.png"
    )
