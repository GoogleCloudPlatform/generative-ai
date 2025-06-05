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

"""Service layer for managing text embeddings.

This module provides the EmbeddingService class, which handles the logic
for creating embedding records in the database. It interacts primarily
with the BigQuery repository.
"""

from src.model.embedding import Embedding
from src.repository.big_query import BigQueryRepository
from typing import List

EMBEDDINGS_TABLE = "embeddings"
INTENTS_TABLE_ID_COLUMN = "id"


class EmbeddingService:
    """Handles business logic related to text embeddings.

    This service interacts with the BigQuery repository to persist
    embedding data.

    Attributes:
        repository: An instance of BigQueryRepository for database operations.
    """

    def __init__(self):
        """Initializes the EmbeddingService with a BigQueryRepository."""
        self.repository = BigQueryRepository()

    def create(self, embedding: Embedding) -> Embedding:
        """Creates a single embedding record in the database.

        Args:
            embedding: The Embedding object to create.

        Returns:
            The created Embedding object.
        """
        schema_fields = Embedding.__schema__()
        column_names = [field.name for field in schema_fields]

        # Prepare values as a tuple, matching the order of schema_fields
        # Ensure the order here matches the order in SearchApplication.__schema__
        values_tuple = (embedding.id, embedding.text, embedding.index, embedding.author)
        self.repository.insert_row(EMBEDDINGS_TABLE, column_names, values_tuple)

        return embedding

    def create_all(self, embeddings: List[Embedding]):
        """Creates multiple embedding records in the database.

        Iterates through the list and calls the `create` method 
        for each embedding.

        Args:
            embeddings: A list of Embedding objects to create.
        """
        for embedding in embeddings:
            self.create(embedding)
