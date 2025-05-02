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
        self.repository.insert_row(
            EMBEDDINGS_TABLE, embedding.to_insert_string()
        )
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
