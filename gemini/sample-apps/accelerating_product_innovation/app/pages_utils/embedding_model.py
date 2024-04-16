"""
Defines functions for generating text embeddings using a Vertex AI TextEmbeddingModel.
"""

from vertexai.preview.language_models import TextEmbeddingModel
import backoff
from google.api_core.exceptions import ResourceExhausted
import numpy as np
import streamlit as st


@st.cache_resource
def get_embedding_model():
    """
    Loads embedding model (to be cached).
    """
    embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko")
    return embedding_model


@backoff.on_exception(backoff.expo, ResourceExhausted, max_time=10)
def embedding_model_with_backoff(text=[]):
    """
    Process embeddings for uploaded files.
    """
    embeddings = get_embedding_model().get_embeddings(text)
    return np.array([each.values for each in embeddings][0])
