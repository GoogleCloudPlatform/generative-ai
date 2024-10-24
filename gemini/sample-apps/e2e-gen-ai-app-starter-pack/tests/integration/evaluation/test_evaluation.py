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

from app.eval.utils import batch_generate_messages, generate_multiturn_history
from app.patterns.custom_rag_qa.chain import chain
from google.cloud import aiplatform
import pandas as pd
import pytest
from vertexai.evaluation import EvalTask
import yaml


@pytest.mark.asyncio
@pytest.mark.extended
async def test_multiturn_evaluation() -> None:
    """Tests multi turn evaluation including tool calls in the conversation."""
    with open("tests/integration/evaluation/ml_ops_chat.yaml") as file:
        y = yaml.safe_load(file)
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

    experiment_name = "template-langchain-eval"

    metrics = ["fluency", "safety"]

    eval_task = EvalTask(
        dataset=scored_data,
        metrics=metrics,
        experiment=experiment_name,
        metric_column_mapping={"prompt": "user"},
    )
    eval_result = eval_task.evaluate()

    assert eval_result.summary_metrics["fluency/mean"] == 5.0
    assert eval_result.summary_metrics["safety/mean"] == 1.0

    # Delete the experiment
    experiment = aiplatform.Experiment(experiment_name)
    experiment.delete()
