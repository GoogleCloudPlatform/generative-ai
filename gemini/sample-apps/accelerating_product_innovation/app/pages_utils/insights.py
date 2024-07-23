"""
This module provides functions for generating insights and searching
relevant information from uploaded data.
    This module:
    * Retrieves relevant context from a vector database based on a user's
      query.
    * Leverages Gemini-Pro to generate a precise answer.
    * Presents the answer along with top-matched context sources.
"""

import json
import os
import re
from typing import Optional

from app.pages_utils.embedding_model import embedding_model_with_backoff
from app.pages_utils.get_llm_response import generate_gemini
from app.pages_utils.pages_config import GLOBAL_CFG
from dotenv import load_dotenv
from google.cloud import storage
import numpy as np
import pandas as pd
import streamlit as st

load_dotenv()


PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# Define storage bucket
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(GLOBAL_CFG["bucket_name"])


def extract_bullet_points(text: str) -> list[str]:
    """
    Extracts all text enclosed within <b> and </b> tags
    or between ** tags from given string.

    Args:
        html_string: The HTML string to process.

    Returns:
        A list containing the extracted text segments.
    """
    pattern = r"(?:<b>([^<]+?)</b>)|(?:\*\*(.+?)\*\*)"
    matches = re.findall(pattern, text)

    # Flatten and filter out empty matches
    bold_text = [match for group in matches for match in group if match.strip()]

    return bold_text


def get_suggestions(state_key: str) -> None:
    """Gets suggestions for the given state key.

    Args:
        state_key (str): The state key to get suggestions for.
    """

    if st.session_state.rag_search_term is None:
        embeddings_df = st.session_state["processed_data_list"].head(2)
        context = "\n".join(embeddings_df["content"].values)
        prompt = f""" Context: \n {context} \n
         generate 5 questions based on the given context
      """
    else:
        context = st.session_state.rag_search_term
        prompt = f""" Context: \n {context} \n
            generate 5 questions based on the given context. The questions
            should strictly be questions for further analysis of
            {st.session_state.rag_search_term}
        """
    gen_suggestions = generate_gemini(prompt)
    st.session_state[state_key] = extract_bullet_points(gen_suggestions)


def get_stored_embeddings_as_df() -> Optional[pd.DataFrame]:
    """Retrieves and processes stored embeddings from cloud storage.

    Returns:
        A Pandas DataFrame containing the embeddings, or None if not found.
    """
    embedding = bucket.blob(st.session_state.product_category + "/embeddings.json")

    if embedding.exists():
        stored_embedding_data = embedding.download_as_string()
        embedding_dataframe = pd.DataFrame.from_dict(json.loads(stored_embedding_data))
        st.session_state["processed_data_list"] = embedding_dataframe
        return embedding_dataframe

    return None


def get_filter_context_from_vector_database(
    question: str, sort_index_value: int = 3
) -> tuple[str, pd.DataFrame]:
    """Gets the filter context from the vector database.

    Args:
        question (str): The question to get the filter context for.
        sort_index_value (int, optional): The number of top matched results
        to return.
        # Defaults to 3.

    Returns:
        tuple: A tuple containing the filter context and the top matched
        results.
    """
    st.session_state["query_vectors"] = np.array(
        embedding_model_with_backoff([question])
    )
    top_matched_score = (
        st.session_state["processed_data_list"]["embedding"]
        .apply(
            lambda row: (
                np.dot(row, st.session_state["query_vectors"]) if row is not None else 0
            )
        )
        .sort_values(ascending=False)[:sort_index_value]
    )

    top_matched_df = st.session_state["processed_data_list"][
        st.session_state["processed_data_list"].index.isin(top_matched_score.index)
    ]
    top_matched_df = top_matched_df[["file_name", "chunk_number", "content"]]
    top_matched_df["confidence_score"] = top_matched_score
    top_matched_df.sort_values(by=["confidence_score"], ascending=False, inplace=True)

    context = "\n".join(
        st.session_state["processed_data_list"][
            st.session_state["processed_data_list"].index.isin(top_matched_score.index)
        ]["content"].values
    )
    return (context, top_matched_df)


def generate_insights_search_result(query: str) -> tuple[str, pd.DataFrame]:
    """Generates insights search results for the given query.

    Args:
        query (str): The query to generate insights search results for.

    Returns:
        tuple: A tuple containing the insights answer and the top matched
        results.
    """

    question = query
    context, top_matched_df = get_filter_context_from_vector_database(
        question=query, sort_index_value=20
    )

    question_prompt_template = f"""
    Answer the question as precise as possible using the provided context.
    If the answer is not contained in the context, say "answer not available
    in context"
    \n \n
    Context: \n {context} \n
    Question: \n {question} \n
    Answer:"""

    insights_answer = generate_gemini(question_prompt_template)
    return insights_answer, top_matched_df.head(5)
