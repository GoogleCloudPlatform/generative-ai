# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Answer QnA Type Questions using genai Content"""

# Utils
import configparser
import logging

from google.cloud import aiplatform
import pandas as pd
from utils import qna_using_query_routing_utils
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel


class QnAVectorSearch:
    """genai Generate Answer From genai Content"""

    def __init__(
        self, config_file: str = "config.ini", logger=logging.getLogger()
    ) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.project_id = self.config["default"]["project_id"]
        self.region = self.config["default"]["region"]
        self.me_region = self.config["vector_search"]["me_region"]
        self.me_index_name = self.config["vector_search"]["me_index_name"]
        self.me_gcs_bucket = self.config["vector_search"]["me_gcs_bucket"]
        self.number_of_references_to_summarise = int(
            self.config["genai_qna"]["number_of_references_to_summarise"]
        )
        self.search_distance_threshould = float(
            self.config["genai_qna"]["search_distance_threshould"]
        )
        self.logger = logger

        # Default retrieval prompt template
        self.prompt_template = """
        SYSTEM: You are genai Programming Language Learning Assistant helping the students answer their questions based on following context. Explain the answers in detail for students.

        Instructions:
        1. Think step-by-step and then answer.
        2. Explain the answer in detail.
        3. If the answer to the question cannot be determined from the context alone, say "I cannot determine the answer to that."
        4. If the context is empty, just say "I could not find any references that are directly related to your question."

        Context:
        =============
        {context}
        =============

        What is the Detailed explanation of answer of following question?
        Question: {question}
        Detailed explanation of Answer:"""  # pylint: disable=line-too-long

    def ask_qna(
        self,
        question: str,
        qna_model: GenerativeModel,
        text_embedding_model: TextEmbeddingModel,
        index_endpoint: aiplatform.MatchingEngineIndexEndpoint,
        deployed_index_id: str,
        embedding_df: pd.DataFrame,
    ) -> str:
        """Retrieves relevant context using vector search and generates an answer using a QnA model.
        Args:
            question (str): The user's question.
            qna_model: The Question Answering model used to generate answers.
            text_embedding_model:  A text embedding model used for similarity search.
            index_endpoint (aiplatform.MatchingEngineIndexEndpoint, optional): The Vertex AI index endpoint.
            deployed_index_id (str, optional): The ID of the deployed index.
            embedding_df (pd.DataFrame): Dataframe containing stored embeddings and document metadata.

        Returns:
            str: The generated answer from the QnA model, or None if no valid answer could be determined.
        """

        # Get the vector search index details
        (
            index_endpoint,
            deployed_index_id,
        ) = qna_using_query_routing_utils.get_deployed_index_id(
            self.config["vector_search"]["me_index_name"],
            self.config["vector_search"]["me_region"],
        )

        self.logger.info("index_endpoint %s:", index_endpoint)
        self.logger.info("deployed_index_id %s:", deployed_index_id)

        # Read context from relavent documents
        context = qna_using_query_routing_utils.find_relavent_context(
            text_embedding_model,
            embedding_df,
            question,
            index_endpoint=index_endpoint,
            deployed_index_id=deployed_index_id,
            num_neighbours=int(
                self.config["genai_qna"]["number_of_references_to_summarise"]
            ),
            similarity_score_threshold=float(
                self.config["genai_qna"]["search_distance_threshould"]
            ),
        )

        # Get response
        response = qna_model.generate_content(
            self.prompt_template.format(context=context, question=question)
        )

        if int(response.candidates[0].finish_reason) == 1:
            answer = response.text
            if answer:
                if (
                    "I cannot determine the answer to that." in answer
                    or "I could not find any references that are directly related to your question."
                    in answer
                ):
                    return ""
                else:
                    return answer
        return ""
