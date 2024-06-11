"""Test Script for DeepEval with Gemini"""
import itertools

from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase
import pytest
from vertex_llm import google_vertexai_gemini_deepeval

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
def test_answer_relevancy(record):
    """Function to test Answer relevancy """
    answer_relevancy_metric = AnswerRelevancyMetric(
        threshold=0.5, model=google_vertexai_gemini_deepeval
    )
    test_case = LLMTestCase(
        input=record["Question"],
        actual_output=record["Answer"],
        retrieval_context=record["Context"],
    )
    assert_test(test_case, [answer_relevancy_metric])
