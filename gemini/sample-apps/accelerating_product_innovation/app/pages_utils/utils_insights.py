"""
This module provides functions for generating insights and searching 
relevant information from uploaded data.
    This module:
    * Retrieves relevant context from a vector database based on a user's query.
    * Leverages Gemini-Pro to generate a precise answer.
    * Presents the answer along with top-matched context sources.
"""

import json
import os
import re

import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.cloud import storage

import app.pages_utils.utils_resources_store_embeddings as utils_resources_store_embeddings
from app.pages_utils.utils_get_llm_response import generate_gemini
from app.pages_utils.embedding_model import embedding_model_with_backoff

load_dotenv()


PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")


def parse_and_format_text(text):
    """Utility funtion to parse and format the LLM generated response.

    Args:
        text (str): The text to parse and format.

    Returns:
        str: The parsed and formatted text.
    """
    bold_pattern = r"\*\*(.*?)\*\*"
    formatted_text = re.sub(bold_pattern, r"<b>\1</b>", text)
    return formatted_text


def extract_bullet_points(text):
    """Extracts bullet points from the LLM generated text.

    Args:
        text (str): The text to extract bullet points from.

    Returns:
        list: A list of bullet points.
    """
    bullet_points = []
    for line in text.splitlines():
        if re.match(r"^[-*•\d]\s*", line):
            bullet_points.append(parse_and_format_text(line))
    return bullet_points


def get_suggestions(state_key):
    """Gets suggestions for the given state key.

    Args:
        state_key (str): The state key to get suggestions for.
    """

    if st.session_state.rag_search_term is None:
        dff = st.session_state["processed_data_list"].head(2)
        context = "\n".join(dff["content"].values)
        prompt = f""" Context: \n {context} \n
         generate 5 questions based on the given context
      """
    else:
        context = st.session_state.rag_search_term
        prompt = f""" Context: \n {context} \n
            generate 5 questions based on the given context. The questions should strictly be questions for further analysis of {st.session_state.rag_search_term}
        """
    print("CONTEXT")
    print(context)
    gen_suggestions = generate_gemini(prompt)
    st.session_state[state_key] = extract_bullet_points(gen_suggestions)


def check_if_file_uploaded():
    """Checks if a file has been uploaded.

    Returns:
        pandas.DataFrame: A DataFrame containing the uploaded file's data.
    """
    project_id = PROJECT_ID
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket("product_innovation_bucket")
    blob = bucket.blob(st.session_state.product_category + "/embeddings.json")
    if blob.exists():
        stored_embedding_data = blob.download_as_string()
        dff = pd.DataFrame.from_dict(json.loads(stored_embedding_data))
        st.session_state["processed_data_list"] = dff
    else:
        dff = pd.DataFrame()
    return dff


def split_text(row):
    """Splits the given text into chunks.

    Args:
        row (pandas.Series): The row to split.

    Returns:
        generator: A generator of chunks.
    """
    chunk_iter = utils_resources_store_embeddings.get_chunks_iter(row, 2000)
    return chunk_iter


def get_dot_product(row):
    """Gets the dot product of the given row and the query vectors.

    Args:
        row (pandas.Series): The row to get the dot product of.

    Returns:
        float: The dot product of the row and the query vectors.
    """
    if row is None:
        return 0
    return np.dot(row, st.session_state["query_vectors"])


def get_filter_context_from_vectordb(question: str = "", sort_index_value: int = 3):
    """Gets the filter context from the vector database.

    Args:
        question (str, optional): The question to get the filter context for. Defaults to "".
        sort_index_value (int, optional): The number of top matched results to return.
        # Defaults to 3.

    Returns:
        tuple: A tuple containing the filter context and the top matched results.
    """
    st.session_state["query_vectors"] = np.array(
        embedding_model_with_backoff([question])
    )
    top_matched_score = (
        st.session_state["processed_data_list"]["embedding"]
        .apply(get_dot_product)
        .sort_values(ascending=False)[:sort_index_value]
    )

    top_matched_df = st.session_state["processed_data_list"][
        st.session_state["processed_data_list"].index.isin(top_matched_score.index)
    ]
    top_matched_df = top_matched_df[
        ["file_name", "page_number", "chunk_number", "content"]
    ]
    top_matched_df["confidence_score"] = top_matched_score
    top_matched_df.sort_values(by=["confidence_score"], ascending=False, inplace=True)

    context = "\n".join(
        st.session_state["processed_data_list"][
            st.session_state["processed_data_list"].index.isin(top_matched_score.index)
        ]["content"].values
    )
    return (context, top_matched_df)


def generate_insights_search_result(query):
    """Generates insights search results for the given query.

    Args:
        query (str): The query to generate insights search results for.

    Returns:
        tuple: A tuple containing the insights answer and the top matched results.
    """

    question = query
    context, top_matched_df = get_filter_context_from_vectordb(
        question=query, sort_index_value=20
    )

    question_prompt_template = f"""
    Answer the question as precise as possible using the provided context. 
    If the answer is not contained in the context, say "answer not available in context" 
    \n \n  
    Context: \n {context} \n
    Question: \n {question} \n
    Answer:"""

    insights_answer = generate_gemini(question_prompt_template)
    return insights_answer, top_matched_df.head(5)
