"""Custom LLM Evaluator"""

import asyncio
from collections.abc import Callable
import logging
import re

from backend.rag.claude_vertex import ClaudeVertexLLM
from google.cloud import bigquery
from llama_index.core.base.response.schema import Response
from llama_index.core.chat_engine.types import AgentChatResponse
import pandas as pd
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
)

logging.basicConfig(level=logging.INFO)  # Set the desired logging level
logger = logging.getLogger(__name__)


class LLMEvaluator:
    """
    LLMEvaluator.evaluate
    LLMEvaluator.async_eval_retrieval
    LLMEvaluator.extract_score
    LLMEvaluator.async_eval_question_answer_pair
    LLMEvaluator.async_eval_answer
    """

    def __init__(
        self,
        system_prompt: str,
        user_prompt: str,
        eval_model_name: str,
        temperature: float,
    ):
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.eval_model_name = eval_model_name

        if "gemini" in self.eval_model_name:
            self.eval_model = GenerativeModel(
                model_name=self.eval_model_name,
                system_instruction=self.system_prompt,
                generation_config=GenerationConfig(
                    temperature=temperature, max_output_tokens=3000
                ),
                safety_settings={
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                },
            )

        elif "claude" in self.eval_model_name:
            self.eval_model = ClaudeVertexLLM(
                project_id="sysco-smarter-catalog",
                region="us-east5",
                model_name="claude-3-5-sonnet@20240620",
                max_tokens=1024,
                system_prompt=self.system_prompt,
            )

    async def async_eval_answer(
        self,
        generative_model: GenerativeModel,
        question: str,
        answer: str,
        ground_truth: str,
        retrieved_context: str,
    ) -> str:
        """
        LLMEvaluator.async_eval_answer
        """
        logger.info(f"Evaluating question: {question}")
        # Stop sequence to cut the model off after outputting an integer
        result = await generative_model.generate_content_async(
            self.user_prompt.format(
                question=question,
                answer=answer,
                ground_truth=ground_truth,
                context=retrieved_context,
            )
        )

        logger.info(f"Finished Evaluating question: {question}")
        return result.text

    async def async_eval_question_answer_pair(
        self,
        retrieval_qa_func,
        eval_model: GenerativeModel,
        question: str,
        ground_truth: str,
    ) -> tuple:
        """
        LLMEvaluator.async_eval_question_answer_pair
        """
        response = await retrieval_qa_func(question)
        if (type(response) == Response) or (type(response) == AgentChatResponse):
            answer = response.response
            retrieved_context = [r.node.text for r in response.source_nodes]
        else:
            retrieved_context = None
            answer = response

        score = await self.async_eval_answer(
            eval_model, question, answer, ground_truth, retrieved_context
        )
        return answer, score, retrieved_context

    @staticmethod
    def extract_score(text: str) -> str | None:
        """
        LLMEvaluator.extract_score
        """
        """Extracts a number (0-100) from the first line of a string.

        Args:
            text (str): The text to search.

        Returns:
            str or None: The extracted number as a string, or None if no number is found.
        """
        first_line = text.splitlines()[0]  # Get the first line
        match = re.search(r"\d{1,3}", first_line)  # Search for a number (1-3 digits)
        if match:
            return int(match.group())  # Return the matched number as a string
        else:
            return 0  # Return None if no number is found

    async def async_eval_retrieval(
        self, retrieval_qa_func: Callable, eval_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        LLMEvaluator.async_eval_retrieval
        """
        results = await asyncio.gather(
            *[
                self.async_eval_question_answer_pair(
                    retrieval_qa_func, self.eval_model, x["question"], x["ground_truth"]
                )
                for idx, x in eval_df[["question", "ground_truth"]].iterrows()
            ]
        )
        answers, eval_result, retrieved_context = list(zip(*results))
        eval_df["answer"] = answers
        eval_df["retrieved_context"] = retrieved_context
        eval_df["eval_result"] = eval_result
        eval_df["score"] = eval_df["eval_result"].apply(lambda x: self.extract_score(x))
        return eval_df

    def evaluate(
        self, retrieval_qa_func: Callable, eval_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        LLMEvaluator.evaluate
        """
        eval_df = asyncio.run(self.async_eval_retrieval(retrieval_qa_func, eval_df))
        return eval_df


def write_results_to_bq(
    pd_dataframe: pd.DataFrame, table_id: str = "eval_results.eval_results_table"
):
    """
    write_results_to_bq
    """
    logger.info("Writing results to BQ...")
    client = bigquery.Client()

    # Define the job configuration
    job_config = bigquery.LoadJobConfig(
        # Automatically detect schema from DataFrame
        autodetect=True,
        # Write disposition (WRITE_TRUNCATE, WRITE_APPEND, WRITE_EMPTY)
        write_disposition="WRITE_APPEND",  # Choose the appropriate disposition
        # Specify the source format (PARQUET, CSV, NEWLINE_DELIMITED_JSON, etc.)
        source_format=bigquery.SourceFormat.PARQUET,
    )

    # Load the DataFrame into BigQuery
    job = client.load_table_from_dataframe(
        pd_dataframe, table_id, job_config=job_config
    )

    # Wait for the job to complete
    logger.info(job.result())
