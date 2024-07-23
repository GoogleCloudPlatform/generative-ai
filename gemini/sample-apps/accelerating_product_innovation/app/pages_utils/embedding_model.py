"""
Defines functions for generating text embeddings using a Vertex AI
TextEmbeddingModel.
"""

import backoff
from google.api_core.exceptions import ResourceExhausted
import numpy as np
import streamlit as st
from vertexai.preview.language_models import TextEmbeddingModel


@st.cache_resource
def get_embedding_model() -> TextEmbeddingModel:
    """
    Loads embedding model (to be cached).
    """
    embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko")
    return embedding_model


@backoff.on_exception(backoff.expo, ResourceExhausted, max_time=10)
def embedding_model_with_backoff(text: list[str]) -> np.ndarray:
    """
    Process embeddings for uploaded files.
    Args:
        text: A list of text strings to process.

    Returns:
        A NumPy array containing the processed embeddings.
    """
    embeddings = get_embedding_model().get_embeddings(text)
    return np.array([each.values for each in embeddings][0])
