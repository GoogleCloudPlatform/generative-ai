import json
from uuid import uuid4
from src.chunk import ChunkService
from langchain_google_vertexai import VertexAIEmbeddings
from typing import List

from google.cloud.aiplatform import (
    MatchingEngineIndexEndpoint,
    MatchingEngineIndex,
)
from src.bigquery import (
    EMBEDDINGS_TABLE,
    INTENTS_TABLE,
    INTENTS_TABLE_ID_COLUMN,
    BigQueryRepository,
)
from src.cloud_storage import (
    EMBEDDINGS_FILE,
    EMBEDDINGS_FOLDER,
    CloudStorageRepository,
)
from src.models import Embedding, Intent
from flask import Request, jsonify
from datetime import datetime
from threading import Thread

INDEX_DIMENSIONS = 768
INDEX_DISTANCE_MEASURE = "DOT_PRODUCT_DISTANCE"
INDEX_NEIGHBORS_COUNT = 150

TEXT_EMBEDDING_MODEL = "textembedding-gecko@003"
EMBEDDINGS_MODEL = VertexAIEmbeddings(TEXT_EMBEDDING_MODEL)

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def create_intent_index(request: Request):
    """
    Handles the HTTP POST request to create embeddings and a Vertex AI Matching Engine index
    for a given intent.

    This function orchestrates the process of:
    1. Retrieving intent details from BigQuery.
    2. Generating text chunks from the intent's source data.
    3. Creating embeddings for each chunk using Vertex AI Embeddings API.
    4. Storing the embeddings in a JSONL file on Google Cloud Storage.
    5. Creating a new Vertex AI Matching Engine index based on the embeddings file.
    6. Storing embedding metadata in BigQuery.
    7. Asynchronously deploying the newly created index to a specified Matching Engine Endpoint.
    8. Updating the intent status in BigQuery throughout the process.

    Args:
        request: The Flask request object, expected to contain a JSON body with
                 'intent_name' and 'index_endpoint_resource'.

    Returns:
        A Flask JSON response indicating success or failure, along with an appropriate
        HTTP status code.
    """
    if request.method != "POST":
        return jsonify({"error": "Method not allowed"}), 405
    try:
        request_json = request.get_json()
        intent_name = request_json.get("intent_name")
        index_resource = request_json.get("index_endpoint_resource")
    except Exception as e:
        return jsonify({"error": "Bad Request"}), 400

    print(f"Event decoded {request_json}", intent_name, index_resource)
    big_query_repository = BigQueryRepository()
    gcs_repository = CloudStorageRepository(big_query_repository.client.project)

    try:
        results = big_query_repository.get_row_by_id(
            INTENTS_TABLE, INTENTS_TABLE_ID_COLUMN, intent_name
        )
        intent = None
        for row in results:
            intent = Intent.__from_row__(row)

        index_endpoint = MatchingEngineIndexEndpoint(index_resource)

        print("Everything has been corretly received")

        index_embeddings = ""
        chunk_service = ChunkService(
            big_query_repository.client.project, intent.gcp_bucket
        )
        embeddings = []

        index_unique_name = f"{intent.name.lower().replace(' ', '-').replace('_','-')}-{uuid4()}"
        chunks = chunk_service.generate_chunks()

        for index, chunk in enumerate(chunks):
            embedding = create_embeddings(chunk)

            if embedding is not None:
                doc_id = f"{intent.name}-{index}.txt"
                embeddings.append(
                    Embedding(
                        id=doc_id,
                        text=chunk,
                        index=index_unique_name,
                        author="system",
                        timestamp=datetime.now().strftime(TIME_FORMAT),
                    )
                )
                index_embeddings += (
                    json.dumps(
                        {
                            "id": doc_id,
                            "embedding": [str(value) for value in embedding],
                        }
                    )
                    + "\n"
                )
        print(f"Embeddings created for {[e.id for e in embeddings]}")
        print(f"Uploading embeddings {intent.name}/{EMBEDDINGS_FILE}")
        gcs_repository.create(
            f"{EMBEDDINGS_FOLDER}/{intent.name}/{EMBEDDINGS_FILE}",
            index_embeddings,
        )

        index = create_index(
            index_unique_name,
            intent.name,
            gcs_repository.bucket_name,
        )
        big_query_repository.update_intent_status(intent_name, "3")
        print("Uploading text chunks to bigquery...")
        big_query_repository.insert_rows(EMBEDDINGS_TABLE, embeddings)
        Thread(
            target=deploy_index_endpoint, args=(index_endpoint, index)
        ).start()
        return jsonify({"message": "JSON received and processed"}), 200

    except Exception as e:
        if index:
            big_query_repository.update_intent_status(intent_name, "4")
        else:
            big_query_repository.update_intent_status(intent_name, "2")
        print(str(e))
        return jsonify({"error": str(e)}), 500


def create_embeddings(chunk: str) -> List[float]:
    """
    Generates embeddings for a given text chunk using the configured Vertex AI model.

    Args:
        chunk: The text string to embed.

    Returns:
        A list of floats representing the embedding vector for the input text,
        or None if embedding fails.
    """
    return EMBEDDINGS_MODEL.embed_query(chunk)


def create_index(index_unique_name: str, intent_name: str, bucket_name: str):
    """
    Creates a new Vertex AI Matching Engine Tree-AH index.

    Args:
        index_unique_name: A unique display name for the index.
        intent_name: The name of the intent associated with this index (used for GCS path).
        bucket_name: The name of the Google Cloud Storage bucket containing the embeddings file.

    Returns:
        A MatchingEngineIndex object representing the newly created index.
    """
    print(f"Creating index: {index_unique_name}")
    return MatchingEngineIndex.create_tree_ah_index(
        display_name=index_unique_name,
        dimensions=INDEX_DIMENSIONS,
        approximate_neighbors_count=INDEX_NEIGHBORS_COUNT,
        distance_measure_type=INDEX_DISTANCE_MEASURE,
        contents_delta_uri=f"gs://{bucket_name}/{EMBEDDINGS_FOLDER}/{intent_name}",
    )


def deploy_index_endpoint(
    index_endpoint: MatchingEngineIndexEndpoint, index: MatchingEngineIndex
):
    """
    Deploys a Matching Engine index to a specified Index Endpoint.

    This function runs asynchronously (intended to be called in a separate thread).

    Args:
        index_endpoint: The MatchingEngineIndexEndpoint object to deploy to.
        index: The MatchingEngineIndex object to deploy.
    """
    print("Deploying index...")
    index_endpoint.deploy_index(
        index=index,
        deployed_index_id=index.display_name.replace("-", "_"),
    )
