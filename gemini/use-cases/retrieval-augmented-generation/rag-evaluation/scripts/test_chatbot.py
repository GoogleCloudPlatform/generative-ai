"""Test Script for DeepEval with Gemini"""

import itertools

from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

# LangChain package for Vertex AI
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory
import pytest
from vertex_llm import GoogleVertexAIDeepEval  # pylint: disable=E0401

# TODO(developer): Update the below lines
PROJECT_ID = "<your_project>"
LOCATION = "<your_region>"

# Initialize safety filters for Gemini model
safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

# Initialize the ChatVertexAI model
custom_model_gemini = ChatVertexAI(
    model_name="gemini-1.0-pro-002",
    safety_settings=safety_settings,
    project=PROJECT_ID,
    location=LOCATION,
    response_validation=False,  # Important since deepeval cannot handle validation errors
)

# Initialize the DeepEval wrapper class
google_vertexai_gemini_deepeval = GoogleVertexAIDeepEval(model=custom_model_gemini)

# Evaluation set with questions and ground_truth
questions = [
    "What architecture is proposed in paper titled Attention is all you need?",
    "Where do primary authors of paper titled Attention is all you need work?",
]
ground_truth = ["Transformers architecture", "Google Brain"]

# Convert into a dataset and prepare for consumption by DeepEval API
test_set = []
for q, a in itertools.zip_longest(questions, ground_truth):
    test_set.append({"Question": q, "Answer": a, "Context": None})


@pytest.mark.parametrize("record", test_set)
def test_answer_relevancy(record: dict) -> None:
    """Function to test Answer relevancy"""
    answer_relevancy_metric = AnswerRelevancyMetric(
        threshold=0.5, model=google_vertexai_gemini_deepeval
    )
    test_case = LLMTestCase(
        input=record["Question"],
        actual_output=record["Answer"],
        retrieval_context=record["Context"],
    )
    assert_test(test_case, [answer_relevancy_metric])
