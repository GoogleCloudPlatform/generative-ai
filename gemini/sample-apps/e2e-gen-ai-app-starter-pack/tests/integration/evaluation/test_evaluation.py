# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=R0801

import json

from app.eval.utils import batch_generate_messages, generate_multiturn_history
from app.patterns.custom_rag_qa.chain import chain
from google.cloud import aiplatform
from langchain_google_vertexai import ChatVertexAI
import pandas as pd
import pytest
from vertexai.evaluation import CustomMetric, EvalTask
import yaml


@pytest.mark.asyncio
async def test_multiturn_evaluation() -> None:
    y = yaml.safe_load(open("tests/integration/evaluation/ml_ops_chat.yaml"))
    df = pd.DataFrame(y)
    df = generate_multiturn_history(df)

    assert len(df) == 2
    assert df["conversation_history"][0] == []
    assert df["human_message"][0]["content"][0]["text"] == "Explain what's MLOps"
    assert len(df["conversation_history"][1]) == 4
    assert (
        df["human_message"][1]["content"][0]["text"] == "How can I evaluate my models?"
    )

    scored_data = batch_generate_messages(df, chain)
    scored_data["user"] = scored_data["human_message"].apply(lambda x: x["content"])
    scored_data["reference"] = scored_data["ai_message"].apply(lambda x: x["content"])

    evaluator_llm = ChatVertexAI(
        model_name="gemini-1.5-flash-001",
        temperature=0,
        response_mime_type="application/json",
    )

    def custom_faithfulness(instance):
        prompt = f"""You are examining written text content. Here is the text:
    ************
    Written content: {instance["response"]}
    ************
    Original source data: {instance["reference"]}

    Examine the text and determine whether the text is faithful or not.
    Faithfulness refers to how accurately a generated summary reflects the essential information and key concepts present in the original source document.
    A faithful summary stays true to the facts and meaning of the source text, without introducing distortions, hallucinations, or information that wasn't originally there.

    Your response must be an explanation of your thinking along with single integer number on a scale of 0-5, 0
    the least faithful and 5 being the most faithful.

    Produce results in JSON

    Expected format:

    ```json
    {{
        "explanation": "< your explanation>",
        "custom_faithfulness": 
    }}
    ```
    """

        result = evaluator_llm.invoke([("human", prompt)])
        result = json.loads(result.content)
        return result

    # Register Custom Metric
    custom_faithfulness_metric = CustomMetric(
        name="custom_faithfulness",
        metric_function=custom_faithfulness,
    )

    experiment_name = "template-langchain-eval"

    metrics = ["fluency", "safety", custom_faithfulness_metric]

    eval_task = EvalTask(
        dataset=scored_data,
        metrics=metrics,
        experiment=experiment_name,
        metric_column_mapping={"prompt": "user"},
    )
    eval_result = eval_task.evaluate()

    assert eval_result.summary_metrics["fluency/mean"] == 5.0
    assert eval_result.summary_metrics["safety/mean"] == 1.0
    assert eval_result.summary_metrics["custom_faithfulness/mean"] > 4.0

    # Delete the experiment
    experiment = aiplatform.Experiment(experiment_name)
    experiment.delete()
