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

from src.model.embedding import Embedding
from src.repository.big_query import BigQueryRepository
from typing import List

EMBEDDINGS_TABLE = "embeddings"
INTENTS_TABLE_ID_COLUMN = "id"

class EmbeddingService:

    def __init__(self):
        self.repository = BigQueryRepository()

    def create(self, embedding: Embedding) -> Embedding:
        schema_fields = Embedding.__schema__()
        column_names = [field.name for field in schema_fields]

        # Prepare values as a tuple, matching the order of schema_fields
        # Ensure the order here matches the order in SearchApplication.__schema__
        values_tuple = (embedding.id, embedding.text, embedding.index, embedding.author)
        self.repository.insert_row(EMBEDDINGS_TABLE, column_names, values_tuple)

        return embedding
    
    def create_all(self, embeddings: List[Embedding]):
        for embedding in embeddings:
            self.create(embedding)
