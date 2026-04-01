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

"""
Evaluation code for document classification use case. This code reads in a 
CSV file with image paths and labels, prepares the data for evaluation, runs 
inference using a specified Gemini model, and then evaluates the predictions 
against the reference labels using the exact match metric in the Generative AI 
Evaluation framework.
"""

import dotenv
import json
import os
import pandas as pd

from google.genai import types
import vertexai

import document_processing


# Load environment variables.
dotenv.load_dotenv()
PROJECT_ID = os.environ.get("GEMINI_PROJECT_ID")
if not PROJECT_ID:
    raise ValueError("GEMINI_PROJECT_ID environment variable must be set.")
LOCATION = os.environ.get("GEMINI_LOCATION", "global")
IMAGE_PATHS = os.environ.get("IMAGE_PATHS", "")
IMAGE_PREFIX = os.environ.get("IMAGE_PREFIX", "")
EVAL_DEST = os.environ.get("EVAL_DEST")

# Other default constants.
EVAL_MODEL = "gemini-2.5-flash"
SAMPLE_SIZE = 10


def load_eval_data(csv_path: str, image_prefix: str) -> pd.DataFrame:
    """Reads eval data from CSV, formats paths, and prepares labels."""
    df = pd.read_csv(csv_path)
    df = df[["img_path", "label"]]
    df["img_path"] = f"{image_prefix}/" + df["img_path"]
    df = df.rename(columns={"label": "reference"})
    return df

def prepare_eval_df(
    csv_path: str, 
    image_prefix: str, 
    sample_size: int = None,
    random_state: int = None,
    stratify: bool = False,
    classes: list[str] = None
) -> pd.DataFrame:
    """Prepares the eval_df based on the data from csv file with image paths."""  
    config_classes = (
        document_processing.CONFIGS["classification_config"]["classes"]
    )

    if classes is None:
        prompt_classes = config_classes
        filter_classes = list(config_classes.keys())
    else:
        prompt_classes = {
            k: v for k, v in config_classes.items() if k in classes
        }
        filter_classes = classes

    prompt = document_processing.CLASSIFY_PROMPT_TEMPLATE.format(
        classes=json.dumps(prompt_classes, indent=4)
    )
    print(prompt)

    df = load_eval_data(csv_path, image_prefix)

    # Filter the DataFrame to only include the requested classes
    df = df[df["reference"].isin(filter_classes)].reset_index(drop=True)

    requests = []
    for uri in df["img_path"]:
        image_part = types.Part.from_uri(
            file_uri=uri,
            mime_type="image/png"
        )
        requests.append([image_part, prompt])
    
    df["request"] = requests
    
    if sample_size and sample_size < len(df):
        if stratify:
            # Proportional stratified sampling per class
            fraction = sample_size / len(df)
            df = df.groupby("reference", group_keys=False).apply(
                lambda x: x.sample(
                    n=max(1, int(round(len(x) * fraction))), 
                    random_state=random_state
                )
            )
            # Correct any slight oversampling due to rounding
            if len(df) > sample_size:
                df = df.sample(n=sample_size, random_state=random_state)
            df = df.reset_index(drop=True)
        else:
            df = df.sample(
                n=sample_size, 
                random_state=random_state
            ).reset_index(drop=True)
    
    return df

def extract_class(response_str):
    """Extract the class from the JSON response."""
    try:
        return json.loads(response_str).get("class")
    except (json.JSONDecodeError, AttributeError):
        return response_str

def run_evaluation(
    project_id: str = PROJECT_ID,
    location: str = LOCATION,
    csv_path: str = IMAGE_PATHS,
    image_prefix: str = IMAGE_PREFIX,
    eval_model: str = EVAL_MODEL,
    sample_size: int = SAMPLE_SIZE,
    random_state: int = 42,
    stratify: bool = False,
    classes: list[str] = None,
    eval_dest: str = EVAL_DEST
):
    client = vertexai.Client(project=project_id, location=location)

    eval_df = prepare_eval_df(
        csv_path=csv_path, 
        image_prefix=image_prefix, 
        sample_size=sample_size,
        random_state=random_state,
        stratify=stratify,
        classes=classes
    )

    eval_dataset = client.evals.run_inference(
        model=eval_model,
        src=eval_df,
        config={
            "generate_content_config": {
                "response_mime_type": "application/json",
                "temperature": 0
            },
            "dest": eval_dest if eval_dest else None
        }
    )

    if hasattr(eval_dataset, "eval_dataset_df"):
        eval_dataset = eval_dataset.eval_dataset_df

    eval_dataset["predicted_class"] = (
        eval_dataset["response"].apply(extract_class)
    )

    # The evaluate function expects 'prompt', 'response', and 'reference'
    # columns, even though the comparison is done between 'response' and 
    # 'reference' only.
    eval_input_df = eval_dataset.copy()
    eval_input_df["response"] = eval_input_df["predicted_class"]
    eval_input_df["prompt"] = "Multimodal classification prompt"
    eval_input_df = (
        eval_input_df[["img_path", "prompt", "response", "reference"]]
    )

    eval_result = (
        client.evals.evaluate(
            dataset=eval_input_df,
            metrics=[vertexai.types.Metric(name='exact_match')],
            config={"dest": eval_dest} if eval_dest else None
        )
    )

    exact_match_scores = [
        case.response_candidate_results[0].metric_results["exact_match"].score 
        for case in eval_result.eval_case_results
    ]

    # Include the original request and the exact match score back into the
    # input DataFrame.

    eval_input_df["exact_match"] = exact_match_scores
    eval_input_df["request"] = eval_dataset["request"]

    # Select and reorder columns for the final results table
    results_df = eval_input_df[
        ["img_path", "response", "reference", "exact_match"]
    ]

    return eval_result, results_df

# if __name__ == "__main__":
#     run_evaluation()
