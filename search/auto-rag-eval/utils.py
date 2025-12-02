
import json
import os
import types
from google.cloud import storage

def convert_to_serializable(obj):
    """Recursively converts an object to a JSON-serializable representation"""
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, types.MappingProxyType):
        return convert_to_serializable(dict(obj))
    elif hasattr(obj, '__dict__'):
        return convert_to_serializable(obj.__dict__)
    else:
        return obj

def save_qa_incrementally(benchmark_entry, output_file):
    """Save a single Q&A entry incrementally to the output file"""
    try:
        # Convert the benchmark entry to the format used by convert_list_to_json
        formatted_entry = {}
        if 'distilled context:' in benchmark_entry:
            formatted_entry['context'] = convert_to_serializable(benchmark_entry['distilled context:'])
        if 'qa gen profile:' in benchmark_entry:
            formatted_entry['Q&A Gen Profile'] = convert_to_serializable(benchmark_entry['qa gen profile:'])

        if 'qa:' in benchmark_entry and isinstance(benchmark_entry['qa:'], dict):
            qa_data = benchmark_entry['qa:']
            if 'question' in qa_data and isinstance(qa_data['question'], dict) and 'question' in qa_data['question']:
                formatted_entry['Question'] = convert_to_serializable(qa_data['question']['question'])
            if 'answer' in qa_data and isinstance(qa_data['answer'], dict) and 'answer' in qa_data['answer']:
                formatted_entry['Answer'] = convert_to_serializable(qa_data['answer']['answer'])

        # Read existing data or initialize new list
        existing_data = []
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []

        # Append new entry
        existing_data.append(formatted_entry)

        # Write back
        with open(output_file, 'w') as f:
            json.dump(existing_data, f, indent=4)

        print(f"[LOGGING] Successfully saved Q&A #{len(existing_data)} to {output_file}")
        return True

    except Exception as e:
        print(f"[LOGGING] Error saving Q&A incrementally: {e}")
        return False

def download_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_name)
        print(f"Blob {source_blob_name} downloaded to {destination_file_name}.")
        return True
    except Exception as e:
        print(f"Error downloading from GCS: {e}")
        return False
