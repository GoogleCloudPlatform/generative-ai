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

    def __init__(self, intents: List[Intent]):
        self.intents_map = {}
        self.questions_embeddings = {}

        for intent in intents:
            self.intents_map[intent.name] = intent
            self.questions_embeddings[intent.name] = EMBEDDINGS_MODEL.embed_documents(
                intent.questions
            )

    def get_intent_from_query(self, query: str) -> Intent:
        # query_embeddings = EMBEDDINGS_MODEL.embed_query(query)
        # m = 0
        # intent = None
        return self.intents_map["Travel concierge"]

        # for intent_name, questions in self.questions_embeddings.items():
        #     similarity = max(cosine_similarity([query_embeddings], questions)[0])
        #     if m < similarity:
        #         m = similarity
        #         intent = self.intents_map[intent_name]
        # return intent

    def get_suggested_questions(self, query: str, intent: Intent) -> List[str]:
        questions = intent.questions
        query_embeddings = EMBEDDINGS_MODEL.embed_query(query)
        similarity = cosine_similarity(
            [query_embeddings], self.questions_embeddings[intent.name]
        )[0]
        suggested_questions = []
        for ix in argsort(similarity)[-3:][::-1]:
            suggested_questions.append(questions[ix])
        return suggested_questions[1:]
