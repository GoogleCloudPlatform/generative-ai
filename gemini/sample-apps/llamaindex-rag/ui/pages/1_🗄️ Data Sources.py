import logging
import os
from typing import Optional

import requests
import streamlit as st
import yaml

logging.basicConfig(
    encoding="utf-8", level=logging.INFO
)  # Set the desired logging level
logger = logging.getLogger(__name__)

# Load configuration
config_path = os.environ.get(
    "CONFIG_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "common", "config.yaml"),
)
with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)

fastapi_url = config["fastapi_url"]


def fetch_vector_search_indexes(qa_or_base: str):
    response = requests.post(
        f"{fastapi_url}/list_vector_search_indexes", json={"qa_or_base": qa_or_base}
    )
    if response.status_code == 200:
        return response.json()
    else:
        st.error(
            "Failed to fetch Vector Search indexes. Please check the server connection."
        )
        return []


def fetch_vector_search_endpoints(qa_or_base: str):
    response = requests.post(
        f"{fastapi_url}/list_vector_search_endpoints", json={"qa_or_base": qa_or_base}
    )
    if response.status_code == 200:
        return response.json()
    else:
        st.error(
            "Failed to fetch Vector Search endpoints. Please check the server connection."
        )
        return []


def fetch_firestore_databases():
    response = requests.get(f"{fastapi_url}/list_firestore_databases")
    if response.status_code == 200:
        return response.json()
    else:
        st.error(
            "Failed to fetch Firestore collections. Please check the server connection."
        )
        return []


def fetch_firestore_collections(selected_database: str):
    response = requests.post(
        f"{fastapi_url}/list_firestore_collections",
        json={"firestore_db_name": selected_database},
    )
    if response.status_code == 200:
        return response.json()
    else:
        st.error(
            "Failed to fetch Firestore collections. Please check the server connection."
        )
        return []


def update_index(
    base_index_name: str,
    base_endpoint_name: str,
    qa_index_name: Optional[str],
    qa_endpoint_name: Optional[str],
    firestore_db_name: Optional[str],
    firestore_namespace: Optional[str],
):
    response = requests.post(
        f"{fastapi_url}/update_index",
        json={
            "base_index_name": base_index_name,
            "base_endpoint_name": base_endpoint_name,
            "qa_index_name": qa_index_name,
            "qa_endpoint_name": qa_endpoint_name,
            "firestore_db_name": firestore_db_name,
            "firestore_namespace": firestore_namespace,
        },
    )
    if response.status_code == 200:
        st.success(f"Updated data source(s) successfully!")
    else:
        st.error("Error updating index.")


st.title("Database and Collection Selector")

# Vector Search Indexes Section
st.subheader("Choose a Vector Search index and endpoint as the base data source.")
vector_indexes = fetch_vector_search_indexes(qa_or_base="base")
if vector_indexes:
    base_selected_index = st.selectbox(
        "Select a Base Vector Search Index",
        index=0,
        options=vector_indexes + [None],
    )
else:
    st.warning("No Vector Search Indexes available.")
    base_selected_index = None
# Vector Search Endpoints Section
vector_endpoints = fetch_vector_search_endpoints(qa_or_base="base")
if vector_endpoints:
    base_selected_endpoint = st.selectbox(
        "Select a Base Vector Search Endpoint",
        index=0,
        options=vector_endpoints + [None],
    )
else:
    st.warning("No Vector Search Endpoints available.")
    base_selected_endpoint = None

st.divider()

st.subheader(
    "Choose a Vector Search index and endpoint as the question answered augmented index."
)
vector_indexes = fetch_vector_search_indexes(qa_or_base="qa")
if vector_indexes:
    qa_selected_index = st.selectbox(
        "Select a QA Vector Search Index",
        index=0,
        options=vector_indexes + [None],
    )
else:
    st.warning("No Vector Search Indexes available.")
    qa_selected_index = None
# Vector Search Endpoints Section
vector_endpoints = fetch_vector_search_endpoints(qa_or_base="qa")
if vector_endpoints:
    qa_selected_endpoint = st.selectbox(
        "Select a QA Vector Search Endpoint", options=vector_endpoints + [None]
    )
else:
    st.warning("No Vector Search Endpoints available.")
    qa_selected_endpoint = None

# Firestore Collections Section
st.subheader("Choose a Firstore database (if applicable)")
firestore_databases = fetch_firestore_databases()
logger.info(firestore_databases)
if firestore_databases:
    selected_database = st.selectbox(
        "Select a Firestore Databases", index=0, options=firestore_databases + [None]
    )
    st.subheader("Choose a FireStore document store to accompany Vector Search.")
    firestore_collections = fetch_firestore_collections(selected_database)
    if firestore_collections:
        selected_collection_namespace = st.selectbox(
            "Select a Firestore Collection",
            index=0,
            options=firestore_collections + [None],
        )
    else:
        st.warning("No Firestore Collections available.")
        selected_collection_namespace = None

else:
    st.warning("No Firestore Databases available.")
    selected_database = None
    selected_collection_namespace = None


# Submit Button
if st.button("Submit Selection"):
    if base_selected_index and base_selected_endpoint:
        update_index(
            base_index_name=base_selected_index,
            base_endpoint_name=base_selected_endpoint,
            qa_index_name=qa_selected_index,
            qa_endpoint_name=qa_selected_endpoint,
            firestore_db_name=selected_database,
            firestore_namespace=selected_collection_namespace,
        )
        st.success("Selection submitted successfully!")
    else:
        st.error("Please select one option from each category before submitting.")
