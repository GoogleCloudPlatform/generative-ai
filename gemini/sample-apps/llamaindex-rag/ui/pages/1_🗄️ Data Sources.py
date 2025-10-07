import logging
import os

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
with open(config_path) as config_file:
    config = yaml.safe_load(config_file)

fastapi_url = config["fastapi_url"]


def fetch_vector_search_data():
    response = requests.get(f"{fastapi_url}/list_vector_search_indexes_and_endpoints")
    if response.status_code == 200:
        return response.json()
    else:
        st.error(
            "Failed to fetch Vector Search data. Please check the server connection."
        )
        return None


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
    qa_index_name: str | None,
    qa_endpoint_name: str | None,
    firestore_db_name: str | None,
    firestore_namespace: str | None,
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
        st.success("Updated data source(s) successfully!")
    else:
        st.error("Error updating index.")


st.title("Database and Collection Selector")

# Vector Search Indexes Section
st.subheader("Choose a Vector Search index and endpoint as the base data source.")
vector_search_data = fetch_vector_search_data()
# Base Vector Search Section
if vector_search_data:
    st.subheader("Choose a Vector Search index and endpoint as the base data source.")
    base_selected_index = st.selectbox(
        "Select a Base Vector Search Index",
        options=vector_search_data["base"]["indexes"],
        index=0,
    )
    base_selected_endpoint = st.selectbox(
        "Select a Base Vector Search Endpoint",
        options=vector_search_data["base"]["endpoints"],
        index=0,
    )

    st.divider()

    # QA Vector Search Section
    st.subheader(
        "Choose a Vector Search index and endpoint as the question answered augmented index."
    )
    qa_selected_index = st.selectbox(
        "Select a QA Vector Search Index",
        options=vector_search_data["qa"]["indexes"],
        index=0,
    )
    qa_selected_endpoint = st.selectbox(
        "Select a QA Vector Search Endpoint",
        options=vector_search_data["qa"]["endpoints"],
        index=0,
    )
else:
    st.warning("Failed to fetch Vector Search data. Please try again later.")

# Firestore Collections Section
st.subheader("Choose a Firestore database (if applicable)")
firestore_databases = fetch_firestore_databases()
logger.info(firestore_databases)
if firestore_databases:
    selected_database = st.selectbox(
        "Select a Firestore Databases", index=0, options=firestore_databases + [None]
    )
    st.subheader("Choose a Firestore document store to accompany Vector Search.")
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
