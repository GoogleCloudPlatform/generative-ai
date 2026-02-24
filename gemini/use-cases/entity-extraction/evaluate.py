import json
import pandas as pd

from google.genai import types
import vertexai

import document_processing


PROJECT_ID = "arielj-argolis-1"
LOCATION = "us-central1"
IMAGE_PATHS = "images.csv"
IMAGE_PREFIX = "gs://arielj-argolis-1-images/dataset"
EVAL_MODEL = "gemini-2.5-flash"
SAMPLE_SIZE = 10


def load_eval_data(csv_path: str, image_prefix: str) -> pd.DataFrame:
    """Reads eval data from CSV, formats paths, and prepares reference labels."""
    df = pd.read_csv(csv_path)
    df = df[["img_path", "label"]]
    df["img_path"] = f"{image_prefix}/" + df["img_path"]
    df = df.rename(columns={"label": "reference"})
    return df

def prepare_eval_df(
    csv_path: str, 
    image_prefix: str, 
    sample_size: int = None
) -> pd.DataFrame:
    """Prepares the eval_df based on the data from csv file with image paths."""  
    classification_classes = (
        document_processing.CONFIGS["classification_config"]["classes"]
    )
    prompt = document_processing.CLASSIFY_PROMPT_TEMPLATE.format(
        classes=json.dumps(classification_classes, indent=4)
    )

    df = load_eval_data(csv_path, image_prefix)
    requests = []
    for uri in df["img_path"]:
        image_part = types.Part.from_uri(
            file_uri=uri,
            mime_type="image/png"
        )
        requests.append([image_part, prompt])
    
    df["request"] = requests
    
    if sample_size and sample_size < len(df):
        df = df.sample(n=sample_size).reset_index(drop=True)
    
    return df

def extract_class(response_str):
    """Extract the class from the JSON response."""
    try:
        return json.loads(response_str).get("class")
    except (json.JSONDecodeError, AttributeError):
        return response_str

def run_evaluation():
    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

    eval_df = prepare_eval_df(
        csv_path=IMAGE_PATHS, 
        image_prefix=IMAGE_PREFIX, 
        sample_size=SAMPLE_SIZE
    )

    eval_dataset = client.evals.run_inference(
        model=EVAL_MODEL,
        src=eval_df,
        config={
            "generate_content_config": {
                "response_mime_type": "application/json",
                "temperature": 0
            }
        }
    )

    if hasattr(eval_dataset, "eval_dataset_df"):
        eval_dataset = eval_dataset.eval_dataset_df

    eval_dataset["predicted_class"] = eval_dataset["response"].apply(extract_class)

    # The evaluate function expects 'prompt', 'response', and 'reference'
    # columns.
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
        )
    )

    exact_match_scores = [
        case.response_candidate_results[0].metric_results["exact_match"].score 
        for case in eval_result.eval_case_results
    ]

    # Include the original request and the exact match score back into the 
    # input dataframe.
    eval_input_df["exact_match"] = exact_match_scores
    eval_input_df["request"] = eval_dataset["request"]

    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 80)

    print(eval_input_df[["img_path", "response", "reference", "exact_match"]])

if __name__ == "__main__":
    run_evaluation()