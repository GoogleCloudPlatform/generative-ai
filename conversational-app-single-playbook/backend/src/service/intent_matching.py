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
