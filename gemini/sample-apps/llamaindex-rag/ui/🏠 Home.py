import streamlit as st

# Set up Streamlit page configuration
st.set_page_config(
    layout="wide", page_title="LlamaIndex RAG Evaluation", page_icon="🏠"
)


# Custom CSS for styling
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
  body { font-family: 'Roboto', sans-serif; background-color: #f0f2f6; }
  .metric-card { border: 1px solid #e1e4e8; border-radius: 10px; padding: 15px; margin-bottom: 10px; background-color: #ffff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.3s ease; }
  .metric-card:hover { transform: translateY(-5px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
  .metric-label { font-size: 16px; font-weight: bold; color: #0366d6; margin-bottom: 5px; }
  .metric-value { font-size: 24px; font-weight: bold; color: #24292e; }
  .top-docs { margin-top: 20px; border-top: 1px solid #e1e4e8; padding-top: 15px; }
  .top-docs h4 { color: #0366d6; margin-bottom: 10px; }
  .doc-title { background-color: #e1e4e8; border-radius: 5px; padding: 5px 10px; margin-bottom: 5px; font-size: 14px; }
  .stSidebar { background-color: #ffff; border-right: 1px solid #e1e4e8; }
  .stSidebar .sidebar-content { padding: 20px; }
  .stSidebar .sidebar-content h1 { color: #0366d6; }
  .stSidebar .sidebar-content .stSelectbox, .stSidebar .sidebar-content .stSlider, .stSidebar .sidebar-content .stNumberInput, .stSidebar .sidebar-content .stCheckbox { margin-bottom: 20px; }
  .stButton>button { background-color: #0366d6; color: #ffff; border: none; border-radius: 5px; padding: 10px 20px; font-size: 16px; cursor: pointer; transition: background-color 0.3s ease; }
  .stButton>button:hover { background-color: #024a9e; }
  .stTextInput>div>div>input { border: 1px solid #e1e4e8; border-radius: 5px; padding: 10px; font-size: 16px; }
  .stTextInput>div>div>input:focus { border-color: #0366d6; box-shadow: 0 0 5px rgba(3, 102, 214, 0.5); }
  .stMarkdown { font-size: 16px; line-height: 1.6; }
  .stMarkdown h3 { color: #0366d6; }
  .stMarkdown h4 { color: #0366d6; }
  .stMarkdown p { color: #24292e; }
  .stMarkdown a { color: #0366d6; text-decoration: none; }
  .stMarkdown a:hover { text-decoration: underline; }
  .stContainer { background-color: #ffff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
  .stContainer .stMarkdown { margin-bottom: 20px; }
  .stContainer .stMarkdown:last-child { margin-bottom: 0; }
  
  
  
</style>
""",
    unsafe_allow_html=True,
)

# Home Page Content
st.title("LlamaIndex RAG Evaluation")
st.markdown(
    """
Welcome to the LlamaIndex RAG Evaluation application. This application leverages:
- **LlamaIndex**: LlamaIndex is a powerful LLM orchestration framework designed for building advanced Large Language Model (LLM) applications, with a particular focus on Retrieval-Augmented Generation (RAG). It provides a comprehensive set of tools and abstractions that simplify the process of ingesting, structuring, and querying various data sources..
- **RAGAS**: RAGAS is a framework which provides some out of the box, heuristic metrics which can be computed given this triple, namely answer faithfulness, answer relevancy, and context relevancy. We compute these on the fly with each chat interaction and display them for the user.
- **Google Gemini Models**: Gemini models are state-of-the-art AI models which excel in natural language understanding and generation, making them useful for a wide range of applications, from chatbots to content creation..
- **Cloud Run**: Google Cloud Run is a fully managed compute platform that automatically scales your stateless containers. It abstracts away the underlying infrastructure, allowing developers to focus on writing code without worrying about server management.

![Architecture](https://i.imgur.com/YjhCWzu.png)
"""
)
