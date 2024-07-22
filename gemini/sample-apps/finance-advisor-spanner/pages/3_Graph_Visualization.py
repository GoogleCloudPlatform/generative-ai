import streamlit as st
import streamlit.components.v1 as components
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
import graph_viz

# Network(notebook=True)
st.subheader("Show me the Relationships between Funds ,Companies and Sectors")
# make Network show itself with repr_html

# def net_repr_html(self):
#  nodes, edges, height, width, options = self.get_network_data()
#  html = self.template.render(height=height, width=width, nodes=nodes, edges=edges, options=options)
#  return html

# Network._repr_html_ = net_repr_html
graph_viz.simple_func_nonx()

HtmlFile = open("Anirban.html", "r", encoding="utf-8")
source_code = HtmlFile.read()
components.html(source_code, height=950, width=900)

with st.sidebar:
    st.subheader("Legend")
    st.image("images/Graph-legend.png")



