# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility file with more generic fuctions"""

import configparser
from datetime import datetime

# Utils
import os
from typing import List

from google.cloud import aiplatform
from langchain.document_loaders import TextLoader, UnstructuredPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_core.documents.base import Document

config_file = "config.ini"
config = configparser.ConfigParser()
config.read(config_file)


def get_deployed_index_id(
    me_index_name: str, location: str
) -> tuple[aiplatform.MatchingEngineIndexEndpoint, str]:
    """
    Retrieves the deployed index ID and index endpoint from Vector Search.

    Checks if a vector search index with the specified name is already deployed in the given location.

    Args:
        me_index_name (str): The name of the Vector Search index.
        location (str): The location where the index is deployed.

    Returns:
        tuple: A tuple containing:
            * aiplatform.MatchingEngineIndexEndpoint: The index endpoint object, or None if not found.
            * str: The deployed index ID, or None if not found.
    """

    index_endpoint_name = me_index_name + "-endpoint"

    list_endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
        filter=f"display_name={index_endpoint_name}", location=location
    )
    if list_endpoints:
        index_endpoint_resource_name = list_endpoints[0].resource_name

        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=index_endpoint_resource_name
        )
        if index_endpoint.deployed_indexes:
            deployed_index_id = index_endpoint.deployed_indexes[0].id
        else:
            deployed_index_id = None
            print(
                f"Index endpoint resource is not available for: {index_endpoint_resource_name}"
            )
    else:
        index_endpoint = deployed_index_id = None
        print(f"Index endpoint is not available for: {index_endpoint_name}")

    return index_endpoint, deployed_index_id


def get_split_documents(index_path: str) -> List[Document]:
    """
    Loads documents from a folder and splits them into manageable chunks.

    Supports both PDF and plain text documents.

    Args:
        index_path (str): The path to the folder containing the document(s).

    Returns:
        List['str']: A list of strings, representing the chunked document(s).
    """

    split_docs = []

    if index_path[-1] != "/":
        index_path = index_path + "/"
    if index_path == "":
        index_path = "."

    for file_name in os.listdir(index_path):
        print(f"Chunking input file: {file_name}")
        if file_name.endswith(".pdf"):
            loader = UnstructuredPDFLoader(index_path + file_name)
        else:
            loader = TextLoader(index_path + file_name)

        text_splitter = CharacterTextSplitter(
            chunk_size=int(config["vector_search"]["chunk_size"]),
            chunk_overlap=int(config["vector_search"]["chunk_overlap"]),
        )
        split_docs.extend(text_splitter.split_documents(loader.load()))

    return split_docs


def create_vector_search_index(
    bucket_uri: str,
) -> tuple[aiplatform.MatchingEngineIndex, aiplatform.MatchingEngineIndexEndpoint, str]:
    """
    Creates a Vertex AI Matching Engine index, endpoint, and deploys the index.

    Args:
        bucket_uri (str): The Cloud Storage bucket URI where embedding data is stored.

    Returns:
        tuple: A tuple containing:
            * aiplatform.MatchingEngineIndex: The created index object.
            * aiplatform.MatchingEngineIndexEndpoint: The created index endpoint object.
            * str: The ID of the deployed index.
    """

    print("Creating new vector search index..")

    UID = datetime.now().strftime("%m%d%H%M")

    # create index
    my_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=config["vector_search"]["me_index_name"],
        location=config["vector_search"]["me_region"],
        contents_delta_uri=bucket_uri,
        dimensions=int(config["vector_search"]["me_dimensions"]),
        approximate_neighbors_count=int(
            config["genai_qna"]["number_of_references_to_summarise"]
        ),
        distance_measure_type="DOT_PRODUCT_DISTANCE",
    )
    print(f"Created new index : {my_index.display_name} with ID: {my_index.name}")

    # create IndexEndpoint
    index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=f'{config["vector_search"]["me_index_name"]}-endpoint',
        public_endpoint_enabled=True,
    )
    print(
        f"Created new index endpoint : {index_endpoint.display_name} with ID: {index_endpoint.name}"
    )

    deployed_index_id = (
        f'{config["vector_search"]["me_index_name"].replace("-", "_")}_deployed_{UID}'
    )

    # deploy the Index to the Index Endpoint
    index_endpoint.deploy_index(index=my_index, deployed_index_id=deployed_index_id)
    print(f"Deployed index to endpoint : {deployed_index_id}")

    return my_index, index_endpoint, deployed_index_id
