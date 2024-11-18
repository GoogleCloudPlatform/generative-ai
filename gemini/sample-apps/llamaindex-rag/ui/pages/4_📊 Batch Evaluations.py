import json
import logging
import os
from tempfile import NamedTemporaryFile

import altair as alt
from google.cloud import storage
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler
import pandas as pd
import requests
import streamlit as st
import yaml

# Set up Google Cloud Storage client
client = storage.Client()

config_path = os.environ.get(
    "CONFIG_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "common", "config.yaml"),
)

# Load the config file
with open(config_path) as file:
    config = yaml.safe_load(file)

fastapi_url = config["fastapi_url"]
BUCKET_NAME = config["rag_eval_dataset"]

# Configure Google Cloud Logging
cloud_client = google.cloud.logging.Client()
handler = CloudLoggingHandler(cloud_client)
cloud_logger = logging.getLogger("cloudLogger")
cloud_logger.setLevel(logging.DEBUG)
cloud_logger.addHandler(handler)


# Function to upload file to GCS
def upload_to_gcs(source_file_name, destination_blob_name):
    try:
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        cloud_logger.info(
            f"File {source_file_name} uploaded to {BUCKET_NAME}/{destination_blob_name}"
        )
        return f"{BUCKET_NAME}/{destination_blob_name}"
    except Exception as e:
        cloud_logger.error(f"Error uploading file to GCS: {str(e)}")
        raise


# Function to call the batch evaluation API
def call_eval_batch_api(payload):
    url = f"{config['fastapi_url']}/eval_batch"
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    cloud_logger.debug(f"Sending request to {url}")
    cloud_logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
    cloud_logger.debug(f"Headers: {headers}")

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=300
        )  # 5-minute timeout
        cloud_logger.debug(f"Response Status Code: {response.status_code}")
        cloud_logger.debug(f"Response Content: {response.text}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        cloud_logger.error("Request timed out")
        st.error(
            "Request timed out. The batch operation might take longer than expected."
        )
    except requests.exceptions.HTTPError as err:
        cloud_logger.error(f"HTTP error occurred: {err}")
        st.error(f"HTTP error occurred: {err}")
    except Exception as err:
        cloud_logger.error(f"An error occurred: {str(err)}")
        st.error(f"An error occurred: {str(err)}")
    return None


# Set up Streamlit page configuration
st.set_page_config(
    layout="wide", page_title="RAG Batch Evaluation", page_icon=":robot_face:"
)

# Sidebar configurations
st.sidebar.markdown("#### 🛠️ Batch Evaluation Configurations")

st.sidebar.markdown("#### 🤖 LLM Model")
llm_name = st.sidebar.selectbox(
    "Select a model:", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
)

st.sidebar.markdown("#### 🤖 Eval LLM Model")
eval_model_name = st.sidebar.selectbox(
    "Select Eval model:", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
)

st.sidebar.markdown("#### 🌡️ Temperature")
temperature = st.sidebar.slider("Adjust temperature:", 0.0, 1.0, 0.2)

st.sidebar.markdown("#### 🔍 Similarity Top K")
similarity_top_k = st.sidebar.number_input(
    "Set top K value:", min_value=1, max_value=20, value=5
)

st.sidebar.markdown("#### 📊 Retrieval Strategy")
retrieval_strategy = st.sidebar.selectbox(
    "Choose strategy:", ["auto_merging", "parent", "baseline"]
)

st.sidebar.markdown("#### 🔧 Advanced Options")
use_hyde = st.sidebar.checkbox("🧠 Use HYDE", value=True)
use_refine = st.sidebar.checkbox("🔬 Use Refine", value=True)
use_node_rerank = st.sidebar.checkbox("🔄 Use Node Rerank", value=True)

st.sidebar.markdown("---")
st.sidebar.warning("🚀 Powered by Google Gemini ♊ Models & LlamaIndex🦙📊!")

# Batch Evaluation Page Content
st.title("RAG Batch Evaluation")
st.markdown(
    "Please modify the configurations before uploading a CSV for batch evaluation. On upload, evaluation is automatically triggered using the LlamaIndex Agentic RAG."
)

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
if uploaded_file is not None:
    try:
        # Save the uploaded file to a temporary file
        with NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_file_path = temp_file.name

        # Upload the file to GCS
        destination_blob_name = f"batch_eval_{uploaded_file.name}"
        gcs_uri = upload_to_gcs(temp_file_path, destination_blob_name)
        st.success(f"File uploaded to {gcs_uri}")

        # Remove the temporary file
        os.unlink(temp_file_path)

        # Prepare the payload for the API call
        payload = {
            "llm_name": llm_name,
            "temperature": temperature,
            "similarity_top_k": similarity_top_k,
            "retrieval_strategy": retrieval_strategy,
            "use_hyde": use_hyde,
            "use_refine": use_refine,
            "use_node_rerank": use_node_rerank,
            "eval_model_name": eval_model_name,
            "embedding_model_name": "text-embedding-004",
            "input_eval_dataset_bucket_uri": gcs_uri,
            "bq_eval_results_table_id": "eval_results.eval_results_table",
            "ragas_metrics": ["faithfulness", "answer_relevancy"],
        }

        # Call the API and get the response
        with st.spinner("Evaluating... This may take a few minutes."):
            response = call_eval_batch_api(payload)

        if response:
            st.success("Evaluation completed!")
            st.markdown("### Evaluation Results")

            # Extract metrics
            scores = response.get("score", [])
            faithfulness_scores = response.get("faithfulness", [])
            answer_relevancy_scores = response.get("answer_relevancy", [])
            questions = response.get("question", [])

            # Create a DataFrame for easier manipulation
            df = pd.DataFrame(
                {
                    "Question": questions,
                    "Overall Score": scores,
                    "Faithfulness": faithfulness_scores,
                    "Answer Relevancy": answer_relevancy_scores,
                }
            )

            # Create an ordered list of questions
            ordered_questions = df["Question"].tolist()

            # Sort the DataFrame based on the original order of questions
            df["Question_Order"] = df["Question"].map(
                {q: i for i, q in enumerate(ordered_questions)}
            )
            df = df.sort_values("Question_Order").drop("Question_Order", axis=1)

            # Display raw data
            st.subheader("Raw Data")
            st.write(df)

            # Create bar graph for the three numeric KPIs
            st.subheader("KPI Scores for Each Question")

            # Normalize Overall Score
            df["Normalized Overall Score"] = df["Overall Score"] / 100

            # Melt the DataFrame to create a long format suitable for Altair
            melted_df = df.melt(
                id_vars=["Question"],
                value_vars=[
                    "Normalized Overall Score",
                    "Faithfulness",
                    "Answer Relevancy",
                ],
                var_name="Metric",
                value_name="Score",
            )

            # Create the bar chart
            chart = (
                alt.Chart(melted_df)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Question:N",
                        sort=ordered_questions,
                        axis=alt.Axis(labelAngle=-45, labelLimit=200),
                    ),
                    y=alt.Y("Score:Q", scale=alt.Scale(domain=[0, 1])),
                    color=alt.Color("Metric:N", scale=alt.Scale(scheme="category10")),
                    xOffset="Metric:N",  # This will group bars for each question side by side
                )
                .properties(
                    width=alt.Step(
                        60
                    ),  # Adjust this value to change the width of the group of bars for each question
                    height=400,
                    title="KPI Scores for Each Question",
                )
            )

            st.altair_chart(chart, use_container_width=True)

            # Add a note about normalization
            st.info(
                "Note: Overall Score has been normalized to a \
                    0-1 range for consistency with other metrics."
            )

            # Individual results
            st.markdown("### Individual Results")
            for i, question in enumerate(ordered_questions):
                row = df[df["Question"] == question].iloc[0]
                with st.expander(f"Question {i+1}"):
                    st.markdown(f"**Question:** {question}")
                    st.markdown(f"**Answer:** {response.get('answer', [])[i]}")
                    st.markdown(
                        f"**Ground Truth:** {response.get('ground_truth', [])[i]}"
                    )
                    st.markdown(f"**Context:** {response.get('contexts', [])[i]}")
                    st.markdown(f"**Overall Score:** {row['Overall Score']:.2f}")
                    st.markdown(f"**Faithfulness:** {row['Faithfulness']:.2f}")
                    st.markdown(f"**Answer Relevancy:** {row['Answer Relevancy']:.2f}")

        else:
            st.warning("No response received from the API.")

    except Exception as e:
        cloud_logger.error(f"An error occurred during the evaluation process: {str(e)}")
        st.error(f"An error occurred during the evaluation process: {str(e)}")
