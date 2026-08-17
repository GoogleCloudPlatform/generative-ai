import json  # noqa: INP001
import types
from pathlib import Path
from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.cloud import storage


def convert_to_serializable(obj: Any) -> Any:
    """Recursively convert an object to a JSON-serializable representation."""
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    if isinstance(obj, types.MappingProxyType):
        return convert_to_serializable(dict(obj))
    if hasattr(obj, "__dict__"):
        return convert_to_serializable(obj.__dict__)
    return obj


def save_qa_incrementally(benchmark_entry: dict[str, Any], output_file: str) -> bool:
    """Save a single Q&A entry incrementally to the output file."""
    try:
        # Convert the benchmark entry to the format used by convert_list_to_json
        formatted_entry: dict[str, Any] = {}
        if "distilled context:" in benchmark_entry:
            formatted_entry["context"] = convert_to_serializable(
                benchmark_entry["distilled context:"]
            )
        if "qa gen profile:" in benchmark_entry:
            formatted_entry["Q&A Gen Profile"] = convert_to_serializable(
                benchmark_entry["qa gen profile:"]
            )

        if "qa:" in benchmark_entry and isinstance(benchmark_entry["qa:"], dict):
            qa_data = benchmark_entry["qa:"]
            if (
                "question" in qa_data
                and isinstance(qa_data["question"], dict)
                and "question" in qa_data["question"]
            ):
                formatted_entry["Question"] = convert_to_serializable(
                    qa_data["question"]["question"]
                )
            if (
                "answer" in qa_data
                and isinstance(qa_data["answer"], dict)
                and "answer" in qa_data["answer"]
            ):
                formatted_entry["Answer"] = convert_to_serializable(
                    qa_data["answer"]["answer"]
                )

        # Read existing data or initialize new list
        output_path = Path(output_file)
        existing_data = []
        if output_path.exists():
            try:
                with output_path.open() as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []

        # Append new entry
        existing_data.append(formatted_entry)

        # Write back
        with output_path.open("w") as f:
            json.dump(existing_data, f, indent=4)

        print(
            f"[LOGGING] Successfully saved Q&A #{len(existing_data)} to {output_file}"
        )
    except (OSError, TypeError, ValueError) as e:
        print(f"[LOGGING] Error saving Q&A incrementally: {e}")
        return False
    else:
        return True


def download_from_gcs(
    bucket_name: str, source_blob_name: str, destination_file_name: str
) -> bool:
    """Download a blob from the bucket."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_name)
        print(f"Blob {source_blob_name} downloaded to {destination_file_name}.")
    except (GoogleAPIError, OSError) as e:
        print(f"Error downloading from GCS: {e}")
        return False
    else:
        return True
