# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Answer QnA Type Questions using genai Content"""

# Utils
import configparser
import logging

from google.cloud import aiplatform
import pandas as pd
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel


class QnAVectorSearch:
    """genai Generate Answer From genai Content"""

    def __init__(
        self,
        model: GenerativeModel,
        index_endpoint: aiplatform.MatchingEngineIndexEndpoint,
        deployed_index_id: str,
        config_file: str,
        logger=logging.getLogger(),
    ) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.logger = logger
        self.model = model
        self.index_endpoint = index_endpoint
        self.deployed_index_id = deployed_index_id

        # Initalizing embedding model
        self.text_embedding_model = TextEmbeddingModel.from_pretrained(
            self.config["vector_search"]["embedding_model_name"]
        )

        self.embedding_df = pd.read_csv(
            self.config["vector_search"]["embedding_csv_file"]
        )

        self.num_neighbors = int(
            self.config["genai_qna"]["number_of_references_to_summarise"]
        )

        # Default retrieval prompt template
        self.prompt_template = """You are a programming language learning assistant, helping the students answer their questions based on the following context. Explain the answer in detail for students.

        Instructions:
        1. Think step-by-step and then answer.
        2. Explain the answer in detail.
        3. If the answer to the question cannot be determined from the context alone, say "I cannot determine the answer to that."
        4. If the context is empty, just say "I could not find any references that are directly related to your question."

        Context:
        =============
        {context}
        =============

        What is the Detailed explanation of the answer to the following question?
        Question: {question}
        Detailed explanation of Answer:"""  # pylint: disable=line-too-long

    def find_relevant_context(self, query: str) -> str:
        """
        Searches the vector index to retrieve relevant context based on a query embedding.

        Args:
            query (str, optional): The query text.

        Returns:
            str: The concatenated text of relevant documents found in the index.
        """

        # Generate the embeddings for user question
        vector = self.text_embedding_model.get_embeddings([query])

        queries = [vector[0].values]

        response = self.index_endpoint.find_neighbors(
            deployed_index_id=self.deployed_index_id,
            queries=queries,
            num_neighbors=self.num_neighbors,
        )

        context = ""
        for neighbor_index in range(len(response[0])):
            context = (
                context
                + self.embedding_df[
                    (self.embedding_df["id"] == response[0][neighbor_index].id)
                    | (self.embedding_df["id"] == int(response[0][neighbor_index].id))
                ].text.values[0]
                + " \n"
            )

        return context

    def ask_qna(self, question: str) -> str:
        """Retrieves relevant context using vector search and generates an answer using a QnA model.
        Args:
            question (str): The user's question.

        Returns:
            str: The generated answer from the QnA model, or None if no valid answer could be determined.
        """

        # Read context from relavent documents
        self.logger.info("QnA: question: %s", question)

        context = self.find_relevant_context(question)
        # self.logger.info("QnA: context: %s", context)

        # Get response
        if len(context) > 0:
            response = self.model.generate_content(
                self.prompt_template.format(context=context, question=question)
            )

            if response and int(response.candidates[0].finish_reason) == 1:
                answer = response.text
                self.logger.info("QnA: response: %s", answer)
                if (
                    "I cannot determine the answer to that." in answer
                    or "I could not find any references that are directly related to your question."
                    in answer
                ):
                    return ""
                else:
                    return answer
        return ""
