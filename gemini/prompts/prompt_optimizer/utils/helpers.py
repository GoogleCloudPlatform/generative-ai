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

import json
import random
import string
import subprocess
from typing import Dict, List, Optional, Tuple, Union

from IPython.display import HTML, Markdown, display
from etils import epath
import pandas as pd
import plotly.graph_objects as go
from tenacity import retry, wait_random_exponential
from vertexai import generative_models
from vertexai.evaluation import EvalTask
from vertexai.generative_models import GenerativeModel

METRICS = [
    "bleu",
    "coherence",
    "exact_match",
    "fluidity",
    "fulfillment",
    "groundedness",
    "rouge_1",
    "rouge_2",
    "rouge_l",
    "rouge_l_sum",
    "safety",
    "question_answering_correctness",
    "question_answering_helpfulness",
    "question_answering_quality",
    "question_answering_relevance",
    "summarization_helpfulness",
    "summarization_quality",
    "summarization_verbosity",
    "tool_name_match",
    "tool_parameter_key_match",
    "tool_parameter_kv_match",
]
COMPOSITE_METRIC = "composite_metric"


def get_id(length: Union[int, None] = 8) -> str:
    """Generate a uuid of a specified length (default=8)."""
    if length is None:
        length = 8
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def get_auth_token() -> None:
    """A function to collect the authorization token"""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-identity-token", "-q"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting auth token: {e}")
        return None


@retry(wait=wait_random_exponential(multiplier=1, max=120))
async def async_generate(prompt: str, model: GenerativeModel) -> Union[str, None]:
    """Generate a response from the model."""
    response = await model.generate_content_async(
        [prompt],
        stream=False,
    )
    return response.text if response.text else None


def evaluate_task(
    df: pd.DataFrame,
    prompt_col: str,
    reference_col: str,
    response_col: str,
    experiment_name: str,
    eval_metrics: List[str],
    eval_sample_n: int,
) -> Dict[str, float]:
    """Evaluate task using Vertex AI Evaluation."""

    # Generate a unique id for the experiment run
    idx = get_id()

    # Rename the columns to match the expected format
    eval_dataset = df[[prompt_col, reference_col, response_col]].rename(
        columns={
            prompt_col: "prompt",
            reference_col: "reference",
            response_col: "response",
        }
    )

    # Drop rows with missing values
    eval_dataset = eval_dataset.dropna()

    # Sample a subset of the dataset
    eval_dataset = eval_dataset.sample(n=eval_sample_n, random_state=8).reset_index(
        drop=True
    )

    # Create an EvalTask object
    eval_task = EvalTask(
        dataset=eval_dataset,
        metrics=eval_metrics,
        experiment=experiment_name,
    )

    # Evaluate the task
    result = eval_task.evaluate(experiment_run_name=f"{experiment_name}-{idx}")

    # Return the summary metrics
    return result.summary_metrics


def print_df_rows(
    df: pd.DataFrame, columns: Optional[List[str]] = None, n: int = 3
) -> None:
    """Print a subset of rows from a DataFrame."""

    # Define the base style for the text
    base_style = (
        "white-space: pre-wrap; width: 800px; overflow-x: auto; font-size: 16px;"
    )

    # Define the header style for the text
    header_style = "white-space: pre-wrap; width: 800px; overflow-x: auto; font-size: 16px; font-weight: bold;"

    # If columns are specified, filter the DataFrame
    if columns:
        df = df[columns]

    # Initialize the counter for printed samples
    printed_samples = 0

    # Iterate over the rows of the DataFrame
    for _, row in df.iterrows():
        for field in df.columns:
            display(HTML(f"<span style='{header_style}'>{field.capitalize()}:</span>"))
            display(HTML("<br>"))
            value = row[field]
            display(HTML(f"<span style='{base_style}'>{value}</span>"))
            display(HTML("<br>"))

        printed_samples += 1
        if printed_samples >= n:
            break


def init_new_model(model_name: str) -> GenerativeModel:
    """Initialize a new model."""

    # Initialize the model
    model = GenerativeModel(
        model_name=model_name,
        generation_config={
            "candidate_count": 1,
            "max_output_tokens": 2048,
            "temperature": 0.5,
        },
        safety_settings={
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_NONE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_NONE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
        },
    )
    return model


def plot_eval_metrics(
    eval_results: List[tuple[str, Dict[str, float]]],
    metrics: Optional[List[str]] = None,
) -> None:
    """Plot a bar plot for the evaluation results."""

    # Create data for the bar plot
    data = []
    for eval_result in eval_results:
        title, summary_metrics = eval_result
        if metrics:
            summary_metrics = {
                k: summary_metrics[k]
                for k, v in summary_metrics.items()
                if any(selected_metric in k for selected_metric in metrics)
            }

        summary_metrics = {k: v for k, v in summary_metrics.items() if "mean" in k}
        data.append(
            go.Bar(
                x=list(summary_metrics.keys()),
                y=list(summary_metrics.values()),
                name=title,
            )
        )

    # Update the figure with the data
    fig = go.Figure(data=data)

    # Add the title
    fig.update_layout(
        title=go.layout.Title(text="Evaluation Metrics", x=0.5),
        xaxis_title="Metric Name",
        yaxis_title="Mean Value",
    )

    # Change the bar mode
    fig.update_layout(barmode="group")

    # Show the plot
    fig.show()


def get_results_file_uris(
    output_uri: str, required_files: List[str] = ["eval_results.json", "templates.json"]
) -> Dict[str, str]:
    """Finds directories containing specific files under the given full GCS path."""

    # Create a path object for the given output URI
    path = epath.Path(output_uri)

    # Initialize a dictionary to store the results file URIs
    results_file_uris: Dict[str, str] = {}

    # Iterate over the directories and files in the path
    for directory in path.iterdir():
        for file in directory.iterdir():
            if file.name in required_files:
                file_key = directory.name + "_" + file.stem
                results_file_uris[file_key] = str(directory / file)

    # Return the results file URIs
    return results_file_uris


def get_best_template(template_uri: str) -> pd.DataFrame:
    """Retrieves and processes the best template."""

    # Load templates from the URI
    with epath.Path(template_uri).open() as f:
        templates = json.load(f)

    # Process metrics for each template
    for template in templates:
        template["metrics"] = {
            key.split("/")[0]: value for key, value in template["metrics"].items()
        }

    # Sort templates based on composite metric or highest metric value
    if any(template["metrics"].get(COMPOSITE_METRIC) for template in templates):
        sorted_templates = sorted(
            templates, key=lambda x: x["metrics"][COMPOSITE_METRIC], reverse=True
        )
    elif any(
        metric in template["metrics"] for template in templates for metric in METRICS
    ):
        sorted_metrics = sorted(
            templates, key=lambda x: max(x["metrics"].values()), reverse=True
        )
        top_metric = list(sorted_metrics[0]["metrics"].keys())[0]
        sorted_templates = sorted(
            templates, key=lambda x: x["metrics"][top_metric], reverse=True
        )
    else:
        raise ValueError("No valid metrics found in templates.")

    # Create a DataFrame with the best template and metrics
    best_template_df = pd.DataFrame([sorted_templates[0]])

    # Add metrics as separate columns
    for metric in best_template_df["metrics"].iloc[0]:
        best_template_df[f"metrics_{metric}"] = best_template_df["metrics"].apply(
            lambda x: x[metric]
        )

    # Drop the 'metrics' column
    best_template_df = best_template_df.drop("metrics", axis=1)

    return best_template_df


def get_best_evaluation(
    best_template_df: pd.DataFrame, eval_result_uri: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Retrieves and processes the best evaluation."""

    # Load the evaluations from the URI
    with epath.Path(eval_result_uri).open() as f:
        evaluations = json.load(f)

    # Get the best index from the best template DataFrame
    best_index = best_template_df["step"].iloc[0]

    # Retrieve the best evaluation based on the index
    best_evaluation: Dict = evaluations[best_index]

    # Create a DataFrame from the summary results
    summary_df = pd.DataFrame([best_evaluation["summary_results"]])

    # Load the metrics table from the best evaluation
    metrics_table = json.loads(best_evaluation["metrics_table"])

    # Create a DataFrame from the metrics table
    metrics_df = pd.DataFrame(metrics_table)

    return summary_df, metrics_df


def get_optimization_result(
    template_uri: str, eval_result_uri: str
) -> Union[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame], None]:
    """Retrieves and processes the best template and evaluation results."""

    # Get the best template DataFrame
    best_template_df = get_best_template(template_uri)

    # Get the summary and metrics DataFrames for the best evaluation
    summary_df, metrics_df = get_best_evaluation(best_template_df, eval_result_uri)

    return best_template_df, summary_df, metrics_df


def display_eval_report(
    eval_result: Union[pd.DataFrame, Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]],
    prompt_component: str = "instruction",
) -> None:
    """Displays evaluation results with optional filtering by metrics."""

    # Unpack the evaluation result
    best_template_df, summary_df, metrics_df = eval_result

    # Display the report title
    display(Markdown("## Vertex AI Prompt Optimizer - Report"))

    # Display the prompt component title
    if prompt_component == "instruction":
        display(Markdown("### Best Instruction"))
    elif prompt_component == "demonstration":
        display(Markdown("### Best Demonstration"))
    else:
        raise ValueError(
            "Invalid prompt_component value. Must be 'instruction' or 'demonstration'."
        )

    # Display the best template DataFrame
    display(best_template_df.style.hide(axis="index"))

    # Display the summary metrics title
    display(Markdown("### Summary Metrics"))
    display(summary_df.style.hide(axis="index"))

    # Display the report metrics title
    display(Markdown("### Report Metrics"))
    display(metrics_df.style.hide(axis="index"))
