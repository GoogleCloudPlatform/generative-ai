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

from langchain_google_vertexai import VertexAIEmbeddings
from vertexai.preview.generative_models import GenerativeModel
from google.cloud import bigquery
from google.cloud.aiplatform import (
    MatchingEngineIndexEndpoint,
    MatchingEngineIndex,
)
from typing import List, MutableSequence
from src.model.intent import Intent
from src.repository.big_query import BIG_QUERY_DATASET, EMBEDDINGS_TABLE
from google.cloud.aiplatform_v1 import (
    FindNeighborsRequest,
    IndexDatapoint,
    MatchServiceClient,
    FindNeighborsResponse,
)

from src.utils.utils import generate_hash, intents_to_json

MATCHING_ENGINE_INDEX_NEIGHBORS = 5

TEXT_EMBEDDING_MODEL = "textembedding-gecko@003"

EMBEDDINGS_MODEL = VertexAIEmbeddings(TEXT_EMBEDDING_MODEL)

INTENTS_HASH = ""
INDEX_ENDPOINTS = {}
INDEX_ENDPOINTS_CLIENTS = {}


class VertexAIService:

    def __init__(self, intents: List[Intent]):
        global INTENTS_HASH
        self.client = bigquery.Client()

        new_hash = generate_hash(intents_to_json(intents))

        if INTENTS_HASH != new_hash:
            for intent in intents:
                if not intent.gcp_bucket:
                    continue
                ixs = MatchingEngineIndexEndpoint.list(
                    filter=f'display_name="{intent.get_standard_name()}"',
                )
                if len(ixs) == 0:
                    print(
                        f"Intent {intent.name} is not yet initialized."
                        "Please run load_indexes.py to create an index"
                        "for the intent"
                    )
                    continue
                INDEX_ENDPOINTS[intent.get_standard_name()] = ixs[0]
                # Configure Vector Search client
                INDEX_ENDPOINTS_CLIENTS[intent.get_standard_name()] = (
                    MatchServiceClient(
                        client_options={
                            "api_endpoint": ixs[0].public_endpoint_domain_name,
                        },
                    )
                )
            INTENTS_HASH = new_hash

    def vector_search_query(
        self,
        index_endpoint: MatchingEngineIndexEndpoint,
        match_service_client: MatchServiceClient,
        question: str,
    ) -> MutableSequence[FindNeighborsResponse.Neighbor]:
        # Build FindNeighborsRequest object
        datapoint = IndexDatapoint(
            feature_vector=EMBEDDINGS_MODEL.embed_query(question)
        )

        query = FindNeighborsRequest.Query(
            datapoint=datapoint, neighbor_count=3
        )

        return (
            match_service_client.find_neighbors(
                FindNeighborsRequest(
                    index_endpoint=index_endpoint.resource_name,
                    deployed_index_id=index_endpoint.deployed_indexes[0].id,
                    # Request can have multiple queries
                    queries=[query],
                    return_full_datapoint=False,
                )
            )
            .nearest_neighbors[0]
            .neighbors
        )

    def get_index_name(
        self, index_endpoint: MatchingEngineIndexEndpoint
    ) -> str:
        return MatchingEngineIndex(
            index_endpoint.deployed_indexes[0].index
        ).display_name

    def get_text_results_from_bigquery(
        self, chunk_ids: List[str], index_name: str
    ):
        if not chunk_ids:
            return []
        query = f"""
            SELECT text, id
             FROM `{BIG_QUERY_DATASET}.{EMBEDDINGS_TABLE}`
             WHERE id IN {str(chunk_ids).replace("[", "(").replace("]", ")")}
             AND index = "{index_name}";
        """

        rows = self.client.query(query).result()
        texts = []

        for row in rows:
            texts.append(row[0])
        return texts

    def generate_llm_response(
        self,
        model: GenerativeModel,
        prompt: str,
        chunked_context,
        question: str,
        temperature: float,
    ) -> str:

        response_list = []
        context = ""
        for ix, data in enumerate(chunked_context):
            context += f"Context {ix + 1}: {data} \n"
        formatted_prompt = f"{prompt} \n {context} Question: {question}"

        responses = model.generate_content(
            formatted_prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": 8192,
                "top_p": 0.95,
            },
            safety_settings=[],
            stream=True,
        )
        for response in responses:
            if response.candidates[0].content.parts:
                response_list.append(response.text)

        return "".join(response_list)

    def generate_out_of_context_response(
        self, model: GenerativeModel, question: str
    ) -> str:
        response_list = []
        prompt = f"""
        You are a friendly conversational bot called. Whenever you are asked a question follow this instructions.
        1. Reply that you don't have an answer for the following question given your knowledge and the context provided in the question.
        2. Ask the user to provide feedback via de UI or to try and rephrase the question.
        3. Apologize and state that you will keep on learning in the future.
        Question: {question}
        """

        responses = model.generate_content(
            prompt,
            generation_config={
                "temperature": 1,
                "max_output_tokens": 8192,
                "top_p": 0.95,
            },
            safety_settings=[],
            stream=True,
        )
        for response in responses:
            if response.candidates[0].content.parts:
                response_list.append(response.text)

        return "".join(response_list)

    def generate_text_from_model(
        self,
        query: str,
        intent: Intent,
    ) -> str:
        """
        Given a user query, and an inferred intent
        we make a similarity search to VectorSearch,
        retrieve the chunked text from bigquery and
        finaly generate an LLM response out of it
        @param query: The user's query
        @param intent: The user's inferred intent
        @return LLM response: The LLM generated response
        """
        model = GenerativeModel(intent.ai_model)
        if intent.gcp_bucket:
            index_endpoint = INDEX_ENDPOINTS[intent.get_standard_name()]
            match_engine_client = INDEX_ENDPOINTS_CLIENTS[
                intent.get_standard_name()
            ]
            similarity_results = self.vector_search_query(
                index_endpoint,
                match_engine_client,
                query,
            )
            if similarity_results:
                context = self.get_text_results_from_bigquery(
                    [res.datapoint.datapoint_id for res in similarity_results],
                    self.get_index_name(index_endpoint),
                )
                return self.generate_llm_response(
                    model,
                    intent.prompt,
                    context,
                    query,
                    intent.ai_temperature,
                )
            else:
                return self.generate_out_of_context_response(model, query)
        else:
            return self.generate_llm_response(
                model,
                intent.prompt,
                [],
                query,
                1,
            )
