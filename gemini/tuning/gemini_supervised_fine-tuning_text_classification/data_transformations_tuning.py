"""
This module provides functions for transforming datasets into the Gemini tuning format.

It includes functions for:
    - Preparing a tuning dataset from a pandas DataFrame.
    - Converting AutoML CSV and JSONL datasets to the Gemini tuning format.
    - Validating a Gemini tuning JSONL file.
"""

import json
from typing import Optional, List, Dict
import pandas as pd
from google.cloud import storage
import gcsfs


def prepare_tuning_dataset_from_df(tuning_df: pd.DataFrame,
                                   system_prompt: Optional[str] = None) -> pd.DataFrame:
    """
    Prepares a tuning dataset from a pandas DataFrame for Gemini fine-tuning.

    This function takes a pandas DataFrame containing text and labels and converts it
    into the Gemini tuning format. It optionally includes a system prompt for zero-shot
    learning.

    Args:
        tuning_df: A pandas DataFrame with columns "text" and "label_text".
        system_prompt_zero_shot: An optional system prompt for zero-shot learning.

    Returns:
        A pandas DataFrame containing the data in the Gemini tuning format.
    """

    tuning_dataset = []
    for _, row in tuning_df.iterrows():
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend([
            {"role": "user", "content": row["text"]},
            {"role": "model", "content": row["label_text"]}
        ])
        tuning_dataset.append({"messages": messages})

    return pd.DataFrame(tuning_dataset)


def convert_tuning_dataset_from_automl_csv(automl_gcs_csv_path: str,
                                           system_prompt: Optional[str] = None,
                                           partition: str = "training") -> pd.DataFrame:
    """
    Converts an AutoML CSV dataset for text classification to the Gemini tuning format.

    This function reads an AutoML JSONL dataset from Google Cloud Storage, filters by partition,
    and converts it to the Gemini tuning format. The Gemini format uses a list of dictionaries,
    each representing a conversation turn with "role" and "content" keys.
    Args:
        automl_gcs_csv_path: The GCS path to the AutoML CSV dataset.
        system_prompt: The instructions to the model.
        partition: The partition to extract from the dataset (e.g., "training",
            "validation", "test"). Defaults to "training".

    Returns:
        A pandas DataFrame containing the data in the Gemini tuning format.
    """

    df = pd.read_csv(automl_gcs_csv_path, names=["partition", "text", "label"])
    df_automl = df.loc[df["partition"] == partition]

    gemini_dataset = []
    for _, row in df_automl.iterrows():
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend([
            {"role": "user", "content": row["text"]},
            {"role": "model", "content": row["label"]}
        ])
        gemini_dataset.append({"messages": messages})

    return pd.DataFrame(gemini_dataset)


def convert_tuning_dataset_from_automl_jsonl(
    project_id: str,
    automl_gcs_jsonl_path: str,
    system_prompt: Optional[str] = None,
    partition: str = "training"
) -> pd.DataFrame:
    """
    Converts an AutoML JSONL dataset for text classification to the Gemini tuning format.

    This function reads an AutoML JSONL dataset from Google Cloud Storage, filters by partition,
    and converts it to the Gemini tuning format. The Gemini format uses a list of dictionaries,
    each representing a conversation turn with "role" and "content" keys.


    Args:
        automl_gcs_jsonl_path: The GCS path to the AutoML JSONL dataset for text classification.
        system_prompt: The instructions to the model.
        partition: The partition to extract from the dataset (e.g., "training",
            "validation", "test"). Defaults to "training".

    Returns:
        A pandas DataFrame containing the data in the Gemini tuning format.
    """
    processed_data = []
    gcs_file_system = gcsfs.GCSFileSystem(project=project_id)
    with gcs_file_system.open(automl_gcs_jsonl_path) as f:
        for line in f:
            data = json.loads(line)
            processed_data.append(
                {
                    "label": data["classificationAnnotation"]["displayName"],
                    "text": data["textContent"],
                    "partition": data["dataItemResourceLabels"][
                        "aiplatform.googleapis.com/ml_use"
                    ]
                }
            )

    df = pd.DataFrame(processed_data)
    df_automl = df.loc[df["partition"] == partition]

    gemini_dataset = []
    for _, row in df_automl.iterrows():
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend([
            {"role": "user", "content": row["text"]},
            {"role": "model", "content": row["label"]}
        ])
        gemini_dataset.append({"messages": messages})

    return pd.DataFrame(gemini_dataset)


def validate_gemini_tuning_jsonl(gcs_jsonl_path: str) -> List[Dict]:
    """
    Validates a JSONL file on Google Cloud Storage against the Gemini tuning format.

    Args:
        gcs_jsonl_path: The GCS path to the JSONL file.

    Returns:
        A list of dictionaries representing the errors found in the file.
        Each dictionary has the following structure:
        {
            "error_type": "Error description",
            "row_index": The index of the row where the error occurred,
            "message": The error message
        }
    """

    errors = []
    storage_client = storage.Client()
    bucket_name = gcs_jsonl_path.split('/')[2]
    blob_name = '/'.join(gcs_jsonl_path.split('/')[3:])
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with blob.open('r') as f:
        for row_index, line in enumerate(f):
            try:
                data = json.loads(line)
                # Check for the presence of the "messages" key
                if "messages" not in data:
                    errors.append({
                        "error_type": "Missing 'messages' key",
                        "row_index": row_index,
                        "message": f"Row {row_index} is missing the 'messages' key."
                    })
                    continue

                messages = data["messages"]
                # Check if "messages" is a list
                if not isinstance(messages, list):
                    errors.append({
                        "error_type": "Invalid 'messages' type",
                        "row_index": row_index,
                        "message": f"Row {row_index}: 'messages' is not a list."
                    })
                    continue

                # Validate each message in the "messages" list
                for message_index, message in enumerate(messages):
                    if not isinstance(message, dict):
                        errors.append({
                            "error_type": "Invalid message format",
                            "row_index": row_index,
                            "message": f"""Row {row_index},
                            message {message_index}: Message is not a dictionary."""
                        })
                        continue

                    # Check for required keys in each message
                    if "role" not in message or "content" not in message:
                        errors.append(
                            {
                                "error_type": "Missing 'role' or 'content' key",
                                "row_index": row_index,
                                "message": f"""Row {row_index}, message {message_index}: 
                                Missing 'role' or 'content' key."""
                            }
                        )
                        continue

                    # Check for valid role values
                    if message["role"] not in ["system", "user", "model"]:
                        errors.append({
                            "error_type": "Invalid 'role' value",
                            "row_index": row_index,
                            "message": f"""Row {row_index}, message {message_index}:
                            Invalid 'role' value. Expected 'system', 'user', or 'model'."""
                        })
                        continue

            except json.JSONDecodeError as e:
                errors.append({
                    "error_type": "JSON Decode Error",
                    "row_index": row_index,
                    "message": f"Row {row_index}: JSON decoding error: {e}"
                })

    return errors
