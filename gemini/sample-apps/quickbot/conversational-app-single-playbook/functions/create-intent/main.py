# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from uuid import uuid4
from src.chunk import ChunkService
from langchain_google_vertexai import VertexAIEmbeddings
from typing import List

from google.cloud.aiplatform import MatchingEngineIndexEndpoint, MatchingEngineIndex
from src.bigquery import EMBEDDINGS_TABLE, INTENTS_TABLE, INTENTS_TABLE_ID_COLUMN, BigQueryRepository
from src.cloud_storage import EMBEDDINGS_FILE, EMBEDDINGS_FOLDER, CloudStorageRepository
from src.models import Embedding, Intent
from flask import Request, jsonify
from datetime import datetime
from threading import Thread

INDEX_DIMENSIONS=768
INDEX_DISTANCE_MEASURE='DOT_PRODUCT_DISTANCE'
INDEX_NEIGHBORS_COUNT=150

TEXT_EMBEDDING_MODEL = "textembedding-gecko@003"
EMBEDDINGS_MODEL = VertexAIEmbeddings(TEXT_EMBEDDING_MODEL)

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

def create_intent_index(request: Request):
    if request.method != 'POST':
        return jsonify({'error': 'Method not allowed'}), 405
    try:
        request_json = request.get_json()
        intent_name = request_json.get('intent_name')
        index_resource = request_json.get('index_endpoint_resource')
    except Exception as e:
        return jsonify({'error': 'Bad Request'}), 400
    
    print(f"Event decoded {request_json}", intent_name, index_resource)
    big_query_repository = BigQueryRepository()
    gcs_repository = CloudStorageRepository(big_query_repository.client.project)
    
    try:        
        results = big_query_repository.get_row_by_id(INTENTS_TABLE, INTENTS_TABLE_ID_COLUMN, intent_name)
        intent = None
        for row in results:
            intent = Intent.__from_row__(row)
        
        index_endpoint = MatchingEngineIndexEndpoint(index_resource)

        print(f"Everything has been corretly received")

        index_embeddings = ""
        chunk_service = ChunkService(big_query_repository.client.project, intent.gcp_bucket)
        embeddings = []
            
        index_unique_name = f"{intent.name.lower().replace(' ', '-').replace('_','-')}-{uuid4()}"
        chunks = chunk_service.generate_chunks()

        for index, chunk in enumerate(chunks):
            embedding = create_embeddings(chunk)

            if embedding is not None:
                doc_id=f"{intent.name}-{index}.txt"
                embeddings.append(Embedding(
                    id=doc_id,
                    text=chunk,
                    index=index_unique_name,
                    author="system",
                    timestamp=datetime.now().strftime(TIME_FORMAT),
                ))
                index_embeddings += json.dumps({
                    "id": doc_id,
                    "embedding": [str(value) for value in embedding],
                }) + "\n"
        print(f"Embeddings created for {[e.id for e in embeddings]}")
        print(f"Uploading embeddings {intent.name}/{EMBEDDINGS_FILE}")
        gcs_repository.create(f"{EMBEDDINGS_FOLDER}/{intent.name}/{EMBEDDINGS_FILE}", index_embeddings)
            
        index = create_index(
            index_unique_name,
            intent.name,
            gcs_repository.bucket_name,
        )
        big_query_repository.update_intent_status(intent_name, "3")
        print("Uploading text chunks to bigquery...")
        big_query_repository.insert_rows(EMBEDDINGS_TABLE, embeddings)
        Thread(target=deploy_index_endpoint, args=(index_endpoint, index)).start()
        return jsonify({'message': 'JSON received and processed'}), 200

    except Exception as e:
        if index:
            big_query_repository.update_intent_status(intent_name, "4")
        else:
            big_query_repository.update_intent_status(intent_name, "2")
        print(str(e))
        return jsonify({'error': str(e)}), 500


def create_embeddings(chunk: str) -> List[float]:
    return EMBEDDINGS_MODEL.embed_query(chunk)

def create_index(index_unique_name: str, intent_name: str, bucket_name: str):
    print(f"Creating index: {index_unique_name}")
    return MatchingEngineIndex.create_tree_ah_index(
        display_name=index_unique_name,
        dimensions=INDEX_DIMENSIONS,
        approximate_neighbors_count=INDEX_NEIGHBORS_COUNT,
        distance_measure_type=INDEX_DISTANCE_MEASURE,
        contents_delta_uri=f"gs://{bucket_name}/{EMBEDDINGS_FOLDER}/{intent_name}",
    )

def deploy_index_endpoint(index_endpoint: MatchingEngineIndexEndpoint, index: MatchingEngineIndex):
    print("Deploying index...")
    index_endpoint.deploy_index(
        index=index,
        deployed_index_id=index.display_name.replace('-','_'),
    )