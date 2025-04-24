from src.model.embedding import Embedding
from src.repository.big_query import BigQueryRepository
from typing import List

EMBEDDINGS_TABLE = "embeddings"
INTENTS_TABLE_ID_COLUMN = "id"

class EmbeddingService:

    def __init__(self):
        self.repository = BigQueryRepository()

    def create(self, embedding: Embedding) -> Embedding:
        self.repository.insert_row(EMBEDDINGS_TABLE, embedding.to_insert_string())
        return embedding
    
    def create_all(self, embeddings: List[Embedding]):
        for embedding in embeddings:
            self.create(embedding)
