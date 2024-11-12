import logging
import os

from google.cloud.logging import Client
from google.cloud.logging.handlers import CloudLoggingHandler
import requests
import streamlit as st
import yaml

config_path = os.environ.get(
    "CONFIG_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "common", "config.yaml"),
)

# Load the config file
with open(config_path) as file:
    config = yaml.safe_load(file)

fastapi_url = config["fastapi_url"]

# Configure Google Cloud Logging
client = Client()
handler = CloudLoggingHandler(client)
cloud_logger = logging.getLogger("cloudLogger")
cloud_logger.setLevel(logging.DEBUG)
cloud_logger.addHandler(handler)

# Get current index info in order to apply logic to prevent bad inputs
try:
    response = requests.get(url=f"{config['fastapi_url']}/get_current_index_info")
    if response.status_code == 200:
        current_index_info = response.json()
    else:
        st.error(
            "Failed to fetch current index info. Check your Vector DBs and Firestore."
        )
except Exception as e:
    print(e)


def verify_user_input(
    current_index_info, retrieval_strategy, qa_followup, hybrid_retrieval
):
    if (current_index_info["firestore_db_name"] is None) or (
        current_index_info["firestore_namespace"] is None
    ):
        if (
            (retrieval_strategy == "auto_merging")
            or (retrieval_strategy == "parent")
            or (hybrid_retrieval == True)
        ):
            raise ValueError(
                "Invalid inputs: No Firestore docstore specified so can't use auto_merging, parent or hybrid retrieval"
            )
    if (current_index_info["qa_index_name"] is None) or (
        current_index_info["qa_endpoint_name"] is None
    ):
        if qa_followup == True:
            raise ValueError(
                "Invalid inputs: No Questions Answered Index specified, can't do qa followup retrieval"
            )


# Function to query FastAPI backend
def query_fastapi(
    query,
    llm_name,
    temperature,
    similarity_top_k,
    retrieval_strategy,
    use_hyde,
    use_refine,
    use_node_rerank,
    qa_followup,
    hybrid_retrieval,
    evaluate_response,
):
    url = f"{config['fastapi_url']}/query_rag"
    payload = {
        "query": query,
        "llm_name": llm_name,
        "temperature": temperature,
        "similarity_top_k": similarity_top_k,
        "retrieval_strategy": retrieval_strategy,
        "use_hyde": use_hyde,
        "use_refine": use_refine,
        "use_node_rerank": use_node_rerank,
        "use_react": use_react,
        "qa_followup": qa_followup,
        "hybrid_retrieval": hybrid_retrieval,
        "evaluate_response": evaluate_response,
        "eval_model_name": "gemini-1.5-flash",
        "embedding_model_name": "text-embedding-004",
    }
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    # Adding debug statements
    cloud_logger.debug(f"URL: {url}")
    cloud_logger.debug(f"Payload: {payload}")
    cloud_logger.debug(f"Headers: {headers}")

    # st.write(f"URL: {url}")
    # st.write(f"Payload: {payload}")
    # st.write(f"Headers: {headers}")

    response = requests.post(url, json=payload, headers=headers, timeout=180)
    cloud_logger.debug(f"Response Status Code: {response.status_code}")
    if response.status_code != 405:
        response.raise_for_status()
        return response.json()
    else:
        cloud_logger.debug(f"Response Content: {response.text}")
        st.write(f"Response Content: {response.text}")
        st.error("Method Not Allowed error")

    return None


def extract_top_titles_and_content(response, num_chunks=3):
    if response and "retrieved_chunks" in response:
        chunks = []
        for chunk in response["retrieved_chunks"][:num_chunks]:
            source = chunk["node"]["metadata"].get("source", "No source available")
            title = source.split("/")[-1] if source else "No title available"
            text = chunk["node"].get("text", "No content available")
            chunks.append({"title": title, "text": text})
        return chunks
    return []


st.set_page_config(
    layout="wide",
    page_title="LlamaIndex Advanced Agentic RAG Implenentation Chatbot",
    page_icon=":speech_balloon:",
)


st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

    body {
        font-family: 'Roboto', sans-serif;
        background-color: #f0f2f6;
    }

    .metric-card {
        border: 1px solid #e1e4e8;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .metric-label {
        font-size: 16px;
        font-weight: bold;
        color: #0366d6;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #24292e;
    }
    .top-docs {
        margin-top: 20px;
        border-top: 1px solid #e1e4e8;
        padding-top: 15px;
    }
    .top-docs h4 {
        color: #0366d6;
        margin-bottom: 10px;
    }
    .doc-title {
        background-color: #e1e4e8;
        border-radius: 5px;
        padding: 5px 10px;
        margin-bottom: 5px;
        font-size: 14px;
    }
    .stSidebar {
        background-color: #ffffff;
        border-right: 1px solid #e1e4e8;
    }
    .stSidebar .sidebar-content {
        padding: 20px;
    }
    .stSidebar .sidebar-content h1 {
        color: #0366d6;
    }
    .stSidebar .sidebar-content .stSelectbox, .stSidebar .sidebar-content .stSlider, .stSidebar .sidebar-content .stNumberInput, .stSidebar .sidebar-content .stCheckbox {
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #0366d6;
        color: #ffffff;
        border: none;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #024a9e;
    }
    .stTextInput>div>div>input {
        border: 1px solid #e1e4e8;
        border-radius: 5px;
        padding: 10px;
        font-size: 16px;
    }
    .stTextInput>div>div>input:focus {
        border-color: #0366d6;
        box-shadow: 0 0 5px rgba(3, 102, 214, 0.5);
    }
    .stMarkdown {
        font-size: 16px;
        line-height: 1.6;
    }
    .stMarkdown h3 {
        color: #0366d6;
    }
    .stMarkdown h4 {
        color: #0366d6;
    }
    .stMarkdown p {
        color: #24292e;
    }
    .stMarkdown a {
        color: #0366d6;
        text-decoration: none;
    }
    .stMarkdown a:hover {
        text-decoration: underline;
    }
    .stContainer {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stContainer .stMarkdown {
        margin-bottom: 20px;
    }
    .stContainer .stMarkdown:last-child {
        margin-bottom: 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


st.markdown(
    """
<style>
    ... (existing styles) ...
    .streamlit-expanderHeader {
        font-size: 14px;
        color: #0366d6;
        background-color: #f6f8fa;
        border: 1px solid #e1e4e8;
        border-radius: 5px;
    }
    .streamlit-expanderContent {
        border: 1px solid #e1e4e8;
        border-top: none;
        border-radius: 0 0 5px 5px;
        padding: 10px;
        font-size: 14px;
        color: #24292e;
    }
    .chunk-content {
        max-height: 200px;
        overflow-y: auto;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("#### 🛠️ RAG Configurations")

st.sidebar.markdown("##### 🤖 LLM Model")
llm_name = st.sidebar.selectbox(
    "Select a model:", ["gemini-1.5-flash", "gemini-1.5-pro", "claude-sonnet-3.5"]
)

st.sidebar.markdown("##### 🌡️ Temperature")
temperature = st.sidebar.slider("Adjust temperature:", 0.0, 1.0, 0.2)

st.sidebar.markdown("##### 🔍 Similarity Top K")
similarity_top_k = st.sidebar.number_input(
    "Set top K value:", min_value=1, max_value=20, value=5
)

st.sidebar.markdown("##### 📊 Retrieval Strategy")
retrieval_strategy = st.sidebar.selectbox(
    "Choose strategy:", ["auto_merging", "parent", "baseline"]
)

st.sidebar.markdown("##### 🔧 Advanced Options")
use_hyde = st.sidebar.checkbox("🧠 Use HYDE", value=True)
use_refine = st.sidebar.checkbox("🔬 Use Refine", value=True)
use_node_rerank = st.sidebar.checkbox("🔄 Use Node Rerank", value=True)
use_react = st.sidebar.checkbox("🕵️‍♂️ Use Agent ReAct", value=True)
evaluate_response = st.sidebar.checkbox("✅ Evaluate Response", value=True)

st.sidebar.markdown("#### Enhancements")
qa_followup = st.sidebar.checkbox("Query Questions Answered Index", value=True)
hybrid_retrieval = st.sidebar.checkbox("Hybrid Retrieval", value=True)

st.sidebar.markdown("---")
st.sidebar.warning("🚀 Powered by Google Gemini ♊ Models & LlamaIndex🦙📊!")


# Initialize metrics in session state
if "metrics" not in st.session_state:
    st.session_state.metrics = {
        "Answer Relevancy": "N/A",
        "Faithfulness": "N/A",
        "Context Relevancy": "N/A",
    }

# Create two columns: one for chat, one for metrics
chat_col, metrics_col = st.columns([2, 1])

# Chat UI
with chat_col:
    st.subheader("LlamaIndex Agentic RAG Implementation Chatbot")

    # Use st.session_state to store messages if not already
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Create a scrollable container for the chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    prompt = st.chat_input("Ask a question:")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:  # Display new messages inside the container
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        verify_user_input(
                            current_index_info,
                            retrieval_strategy=retrieval_strategy,
                            qa_followup=qa_followup,
                            hybrid_retrieval=hybrid_retrieval,
                        )
                        response = query_fastapi(
                            prompt,
                            llm_name,
                            temperature,
                            similarity_top_k,
                            retrieval_strategy,
                            use_hyde,
                            use_refine,
                            use_node_rerank,
                            qa_followup,
                            hybrid_retrieval,
                            evaluate_response,
                        )

                        if response is not None:
                            assistant_response = response.get(
                                "response",
                                "No response content received from the server.",
                            )
                            st.markdown(assistant_response)
                            if evaluate_response:
                                st.session_state.metrics = {
                                    "Answer Relevancy": response.get(
                                        "answer_relevancy", "N/A"
                                    ),
                                    "Faithfulness": response.get("faithfulness", "N/A"),
                                    "Context Relevancy": response.get(
                                        "context_relevancy", "N/A"
                                    ),
                                }
                            # st.session_state.top_titles = extract_top_titles(response)
                            st.session_state.chunks = extract_top_titles_and_content(
                                response
                            )
                            st.session_state.messages.append(
                                {"role": "assistant", "content": assistant_response}
                            )
                        else:
                            st.error(
                                "Failed to get a response from the server. Please check the server status and try again."
                            )
                    except ValueError as e:
                        st.error(e)

# Display evaluation metrics in the right column
with metrics_col:
    st.markdown(
        "<h3 style='text-align: center; color: #0366d6;'>Evaluation Metrics</h3>",
        unsafe_allow_html=True,
    )
    metrics_container = st.container()
    with metrics_container:
        for metric, value in st.session_state.metrics.items():
            formatted_value = f"{value:.2f}" if isinstance(value, float) else value
            st.markdown(
                f"""
            <div class="metric-card">
                <p class="metric-label">{metric}</p>
                <p class="metric-value">{formatted_value}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Display top titles and expandable chunks
        if hasattr(st.session_state, "chunks"):
            st.markdown('<div class="top-docs">', unsafe_allow_html=True)
            st.markdown("<h4>Top Retrieved Documents</h4>", unsafe_allow_html=True)
            for i, chunk in enumerate(st.session_state.chunks, 1):
                with st.expander(f"{i}. {chunk['title']}"):
                    st.markdown(
                        f'<div class="chunk-content">{chunk["text"]}</div>',
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)
