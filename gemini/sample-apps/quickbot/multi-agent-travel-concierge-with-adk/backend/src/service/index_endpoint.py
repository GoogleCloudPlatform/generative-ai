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

from typing import List
from google.cloud.aiplatform import MatchingEngineIndexEndpoint
from src.repository.big_query import BigQueryRepository
from src.service.vertex_ai import EMBEDDINGS_MODEL

BIG_QUERY_ID_COLUMN = "id"
BIG_QUERY_INDEX_COLUMN = "index"
BIG_QUERY_TEXT_COLUMN = "text"
BIG_QUERY_AUTHOR_COLUMN = "author"
BIG_QUERY_TIMESTAMP_COLUMN = "timestamp"

INDEX_DIMENSIONS=768
INDEX_DISTANCE_MEASURE='DOT_PRODUCT_DISTANCE'
INDEX_NEIGHBORS_COUNT=150

class IndexEndpointService:

    def __init__(self):
        self.bq_repository = BigQueryRepository()

    def get_endpoint(self, name: str) -> MatchingEngineIndexEndpoint:
        index_endpoints = MatchingEngineIndexEndpoint.list(
            filter=f'display_name="{name}"',
        )

        if index_endpoints:
            return index_endpoints[0]
        else:
            raise Exception(f"Matching Engine Index Endpoint with name {name} doesn't exist")

    def create_endpoint(self, name: str) -> MatchingEngineIndexEndpoint:
        return MatchingEngineIndexEndpoint.create(
            display_name=name,
            description=name,
            public_endpoint_enabled=True,
        )

    def delete_endpoint(self, endpoint: MatchingEngineIndexEndpoint) -> MatchingEngineIndexEndpoint:
        MatchingEngineIndexEndpoint.delete(endpoint, force=True)

    def create_embeddings(self, chunk: str) -> List[float]:
        return EMBEDDINGS_MODEL.embed_query(chunk)
    
    def endpoint_has_deployed_indexes(self, name: str) -> bool:
        index_endpoint = self.get_endpoint(name)
        return len(index_endpoint.deployed_indexes) > 0