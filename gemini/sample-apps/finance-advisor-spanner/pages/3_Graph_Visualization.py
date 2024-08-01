"""This module is the page for Graph Visualization feature"""

# pylint: disable=line-too-long, invalid-name, import-error, use-dict-literal

import graph_viz
import streamlit as st
import streamlit.components.v1 as components

st.subheader("Show me the Relationships between Funds ,Companies and Sectors")


graph_viz.generate_graph()

html_file = open("graph_viz.html", "r", encoding="utf-8")
source_code = html_file.read()
components.html(source_code, height=950, width=900)

with st.sidebar:
    st.subheader("Legend")
    st.image(
        "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/Graph-legend.png"
    )
