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
"""Evaluating PydanticAI Agents Tool Use and Trajectories with Vertex AI

The tutorial uses the following Google Cloud services and resources:

* Vertex AI Generative AI Evaluation

The steps performed include:

* Build local agent using PydanticAI
* Prepare Agent Evaluation dataset
* Single tool usage evaluation
* Trajectory evaluation
* Response evaluation

Create a virtual environment and install prerquisites:

```
pip install google-cloud-aiplatform[evaluation]>=1.78.0" "pandas>=2.2.3" "pydantic-ai-slim[vertexai]>=0.0.20"
```

Then, you'll be able to run this python script to exercise evaluating a PydanticAI agent with the Vertex AI Generative AI Evaluation Service SDK.

"""

import os
import random
import string

import pandas as pd
from google.cloud import aiplatform
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.vertexai import VertexAIModel
from pydantic_ai.result import RunResult
from vertexai.preview.evaluation import EvalTask
from vertexai.preview.evaluation.metrics import (
    PointwiseMetric,
    PointwiseMetricPromptTemplate,
    TrajectorySingleToolUse,
)

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.environ.get("LOCATION", "us-central1")
EXPERIMENT_NAME = "evaluate-pydanticai-agent"

# PydanticAI Agent definition
model = VertexAIModel("gemini-1.5-flash", project_id=PROJECT_ID, region=LOCATION)

agent = Agent(
    model,
    system_prompt="Be concise, reply with one sentence.",
)


@agent.tool
def get_product_details(ctx: RunContext[str], product_name: str):  # pylint: disable=unused-argument
    """Gathers basic details about a product."""
    details = {
        "smartphone": "A cutting-edge smartphone with advanced camera features and lightning-fast processing.",
        "usb charger": "A super fast and light usb charger",
        "shoes": "High-performance running shoes designed for comfort, support, and speed.",
        "headphones": "Wireless headphones with advanced noise cancellation technology for immersive audio.",
        "speaker": "A voice-controlled smart speaker that plays music, sets alarms, and controls smart home devices.",
    }
    return details.get(product_name, "Product details not found.")


@agent.tool
def get_product_price(ctx: RunContext[str], product_name: str):  # pylint: disable=unused-argument
    """Gathers price about a product."""
    details = {
        "smartphone": 500,
        "usb charger": 10,
        "shoes": 100,
        "headphones": 50,
        "speaker": 80,
    }
    return details.get(product_name, "Product price not found.")


print("PydanticAI agent created.")


# Helper methods for evaluation
def get_id(length: int = 8) -> str:
    """Generate a uuid of a specified length (default=8)."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def parse_messages_to_output_dictionary(result: RunResult) -> dict:
    """Takes a full Result log of a PydanticAI agent interaction and extracts tool use
    Args:
        PydanticAI RunResult
    Returns:
        dictionary of agent response, ready for tool evaluation
    """

    final_output = {
        "response": "No AI response found in the message history.",
        "predicted_trajectory": [],
    }

    function_calls = []
    try:
        for message in result.all_messages():
            if message.kind == "response":
                if message.parts[0].part_kind == "tool-call":
                    function_calls.append(
                        {
                            "tool_name": message.parts[0].tool_name,
                            "tool_input": message.parts[0].args.args_dict,
                        }
                    )
                if message.parts[0].part_kind == "text":
                    final_output["response"] = message.parts[0].content

        final_output["predicted_trajectory"] = function_calls

    except AttributeError as e:
        final_output["error"] = f"Agent does not have tool_results: {e}"
        print(f"Error: {e}")

    return final_output


def agent_parsed_outcome(prompt: str):
    """Invoke agent and get tool outputs for evaluation
    Args:
        input prompt: str
    Returns:
        output dictionary of agent response, ready for tool evaluation
    """
    result = agent.run_sync(prompt)

    return parse_messages_to_output_dictionary(result)


print("Sample runs of agent:")
print("prompt: Get price for smartphone")
print(agent_parsed_outcome(prompt="Get price for smartphone"))
# print("prompt: Get product details and price for headphones")
# print(agent_parsed_outcome(prompt='Get product details and price for headphones'))
print()

# Evaluation

# Evaluation dataset
eval_data = {
    "prompt": [
        "Get price for smartphone",
        "Get product details and price for headphones",
        "Get details for usb charger",
        "Get product details and price for shoes",
        "Get product details for speaker?",
    ],
    "reference_trajectory": [
        [
            {
                "tool_name": "get_product_price",
                "tool_input": {"product_name": "smartphone"},
            }
        ],
        [
            {
                "tool_name": "get_product_details",
                "tool_input": {"product_name": "headphones"},
            },
            {
                "tool_name": "get_product_price",
                "tool_input": {"product_name": "headphones"},
            },
        ],
        [
            {
                "tool_name": "get_product_details",
                "tool_input": {"product_name": "usb charger"},
            }
        ],
        [
            {
                "tool_name": "get_product_details",
                "tool_input": {"product_name": "shoes"},
            },
            {"tool_name": "get_product_price", "tool_input": {"product_name": "shoes"}},
        ],
        [
            {
                "tool_name": "get_product_details",
                "tool_input": {"product_name": "speaker"},
            }
        ],
    ],
}

eval_sample_dataset = pd.DataFrame(eval_data)
print("Sample dataset loaded. First three rows:")
print(eval_sample_dataset.head(3))

# Evaluation methodologies for tool calling


def single_tool_evaluation() -> None:
    """Single tool usage evaluation
    Determines of a single tool was appropriately selected
    """

    print("Single tool usage evaluation")

    single_tool_usage_metrics = [TrajectorySingleToolUse(tool_name="get_product_price")]
    experiment_run = f"single-metric-eval-{get_id()}"

    single_tool_call_eval_task = EvalTask(
        dataset=eval_sample_dataset,
        metrics=single_tool_usage_metrics,
        experiment=EXPERIMENT_NAME,
    )

    single_tool_call_eval_result = single_tool_call_eval_task.evaluate(
        runnable=agent_parsed_outcome,
        experiment_run_name=experiment_run,
    )

    print("Summary metrics")
    metrics_df = pd.DataFrame.from_dict(
        single_tool_call_eval_result.summary_metrics, orient="index"
    ).T
    print(metrics_df)


def trajectory_evaluation() -> None:
    """Trajectory evaluation
    Determines if the order of tool choice is reasonable
    """

    print("Tool trajectory evaluation")

    trajectory_metrics = [
        "trajectory_exact_match",
        "trajectory_in_order_match",
        "trajectory_any_order_match",
        "trajectory_precision",
        "trajectory_recall",
    ]

    experiment_run = f"trajectory-{get_id()}"

    trajectory_eval_task = EvalTask(
        dataset=eval_sample_dataset,
        metrics=trajectory_metrics,
        experiment=EXPERIMENT_NAME,
    )

    trajectory_eval_result = trajectory_eval_task.evaluate(
        runnable=agent_parsed_outcome, experiment_run_name=experiment_run
    )

    print("Summary metrics")
    metrics_df = pd.DataFrame.from_dict(
        trajectory_eval_result.summary_metrics, orient="index"
    ).T
    print(metrics_df)


def final_response_evaluation() -> None:
    """Final response evaluation
    Determine if the final response is correct
    """

    print("Final response from tool use evaluation")

    response_metrics = ["safety", "coherence"]

    experiment_run = f"response-{get_id()}"

    response_eval_task = EvalTask(
        dataset=eval_sample_dataset,
        metrics=response_metrics,
        experiment=EXPERIMENT_NAME,
    )

    response_eval_result = response_eval_task.evaluate(
        runnable=agent_parsed_outcome, experiment_run_name=experiment_run
    )

    print("Summary metrics")
    metrics_df = pd.DataFrame.from_dict(
        response_eval_result.summary_metrics, orient="index"
    ).T
    print(metrics_df)


def custom_metric() -> None:
    """Custom metric evaluation - logical following
    Use a prompt as criteria for evaluation
    """

    criteria = {
        "Follows trajectory": (
            "Evaluate whether the agent's response logically follows from the "
            "sequence of actions it took. Consider these sub-points:\n"
            "  - Does the response reflect the information gathered during the trajectory?\n"
            "  - Is the response consistent with the goals and constraints of the task?\n"
            "  - Are there any unexpected or illogical jumps in reasoning?\n"
            "Provide specific examples from the trajectory and response to support your evaluation."
        )
    }

    pointwise_rating_rubric = {
        "1": "Follows trajectory",
        "0": "Does not follow trajectory",
    }

    response_follows_trajectory_prompt_template = PointwiseMetricPromptTemplate(
        criteria=criteria,
        rating_rubric=pointwise_rating_rubric,
        input_variables=["prompt", "predicted_trajectory"],
    )

    response_follows_trajectory_metric = PointwiseMetric(
        metric="response_follows_trajectory",
        metric_prompt_template=response_follows_trajectory_prompt_template,
    )

    response_tool_metrics = [
        "trajectory_exact_match",
        "trajectory_in_order_match",
        "safety",
        response_follows_trajectory_metric,
    ]
    experiment_run = f"response-over-tools-{get_id()}"

    response_eval_tool_task = EvalTask(
        dataset=eval_sample_dataset,
        metrics=response_tool_metrics,
        experiment=EXPERIMENT_NAME,
    )

    response_eval_tool_result = response_eval_tool_task.evaluate(
        runnable=agent_parsed_outcome, experiment_run_name=experiment_run
    )

    print("Summary metrics")
    metrics_df = pd.DataFrame.from_dict(
        response_eval_tool_result.summary_metrics, orient="index"
    ).T
    print(metrics_df)


def delete_experiment(experiment_name: str):
    """Delete the experiment
    Used as a cleanup mechanism"""
    try:
        experiment = aiplatform.Experiment(experiment_name)
        experiment.delete(delete_backing_tensorboard_runs=True)
    except Exception as e:
        print(e)


def main():
    """Main function"""
    single_tool_evaluation()
    trajectory_evaluation()
    final_response_evaluation()
    custom_metric()
    # delete_experiment(EXPERIMENT_NAME)


if __name__ == "__main__":
    main()
