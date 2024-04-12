# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Utility file with more generic fuctions"""

# Utils
import os
import time
import configparser
import pandas as pd
from typing import List
from datetime import datetime

from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

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


def find_relavent_context(
    text_embedding_model: TextEmbeddingModel,
    embedding_df: pd.DataFrame,
    query: str,
    index_endpoint: aiplatform.MatchingEngineIndexEndpoint,
    deployed_index_id: str,
    num_neighbours: int = 5,
    similarity_score_threshold: float = 0.0,
) -> str:
    """
    Searches the vector index to retrieve relevant context based on a query embedding.

    Args:
        text_embedding_model: The model used to generate text embeddings.
        embedding_df (pd.DataFrame): DataFrame containing stored embeddings and associated metadata.
        query (str, optional): The query text.
        index_endpoint (aiplatform.MatchingEngineIndexEndpoint, optional): The Vertex AI index endpoint.
        deployed_index_id (str, optional): The ID of the deployed index.
        num_neighbours (int, optional): The number of nearest neighbors to retrieve.Defaults to 5.
        similarity_score_threshold (float, optional):  Minimum similarity score threshold. Defaults to 0.0.

    Returns:
        str: The concatenated text of relevant documents found in the index.
    """

    # Generate the embeddings for user question
    vector = text_embedding_model.get_embeddings([query])
    user_query_embedding = [vector[0].values]

    response = index_endpoint.find_neighbors(
        deployed_index_id=deployed_index_id,
        queries=user_query_embedding,
        num_neighbors=num_neighbours,
    )

    context = ""
    for neighbor_index in range(len(response[0])):
        context = (
            context
            + embedding_df[
                embedding_df["id"] == response[0][neighbor_index].id
            ].text.values[0]
            + " \n"
        )

    return context


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
        print(f"file_name : {file_name}")
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


def generate_embeddings(
    document_folder: str, text_embedding_model: TextEmbeddingModel
) -> pd.DataFrame:
    """
    Generates text embeddings from documents and saves them to a CSV file.

    Args:
        document_folder (str): Path to the folder containing the documents.
        text_embedding_model: A text embedding model.

    Returns:
        pd.DataFrame: The DataFrame containing the generated embeddings and associated metadata.
    """

    doc_splits = get_split_documents(document_folder)

    for idx, split in enumerate(doc_splits):
        split.metadata["chunk"] = idx

    # Log the number of documents after splitting
    print(f"# of documents = {len(doc_splits)}")

    texts = [doc.page_content for doc in doc_splits]
    text_embeddings_list = []
    id_list = []
    page_source_list = []
    for doc in doc_splits:
        embeddings = text_embedding_model.get_embeddings([doc.page_content])
        vector = embeddings[0].values
        text_embeddings_list.append(vector)
        # id_list.append(str(id))
        id_list.append(f'{doc.metadata["source"]}_{doc.metadata["chunk"]}')
        page_source_list.append(doc.metadata["source"])
        time.sleep(1)  # So that we don't run into Quota Issue
        if len(id_list) % 100 == 0:
            print("\nprocessing document chunk no :", doc.metadata["chunk"])
        else:
            print(".", end="", sep=" ")

    # Creating a dataframe of ID, embeddings, page_source and text
    embedding_df = pd.DataFrame(
        {
            "id": id_list,
            "embedding": text_embeddings_list,
            "page_source": page_source_list,
            "text": texts[: len(id_list)],
        }
    )

    embedding_df.to_csv(config["vector_search"]["embedding_csv_file"], index=False)

    return embedding_df


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
