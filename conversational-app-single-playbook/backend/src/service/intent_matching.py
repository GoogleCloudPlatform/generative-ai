from numpy import argsort
from langchain.utils.math import cosine_similarity
from src.model.intent import Intent
from src.service.vertex_ai import EMBEDDINGS_MODEL
from typing import List


class IntentMatchingService:

    def get_suggested_questions(self, query: str, intent: Intent) -> List[str]:
        query_embeddings = EMBEDDINGS_MODEL.embed_query(query)
        questions_embeddings = EMBEDDINGS_MODEL.embed_documents(
            intent.questions
        )
        similarity = cosine_similarity(
            [query_embeddings], questions_embeddings
        )[0]
        suggested_questions = []
        for ix in argsort(similarity)[-3:][::-1]:
            suggested_questions.append(intent.questions[ix])
        return suggested_questions[1:]
