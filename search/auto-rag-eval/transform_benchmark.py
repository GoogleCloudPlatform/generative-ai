#!/usr/bin/env python3
"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


Benchmark Data Transformation Script

This script transforms a source benchmark file into the desired format for evaluation.

The transformation follows this mapping:
- query (target) <-- Question (source)
- expected_tool_use (target) <-- [] (empty list)
- reference (target) <-- Answer (source)
"""

import json
import argparse
import sys
from pathlib import Path


def transform_benchmark_data(source_records):
    """
    Transforms a list of source benchmark records to the target format.

    Args:
        source_records: A list of dictionaries in the source format.

    Returns:
        A list of dictionaries in the target format.
    """
    transformed_data = []
    skipped_count = 0

    for i, record in enumerate(source_records):
        if "Question" in record and "Answer" in record:
            transformed_record = {
                "query": record["Question"],
                "expected_tool_use": [],
                "reference": record["Answer"]
            }
            transformed_data.append(transformed_record)
        else:
            print(f"Warning: Skipping record {i+1} due to missing 'Question' or 'Answer' fields")
            skipped_count += 1

    if skipped_count > 0:
        print(f"\nTotal records skipped: {skipped_count}")

    return transformed_data


def main():
    parser = argparse.ArgumentParser(
        description="Transform benchmark data from source format to target format"
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the source benchmark JSON file"
    )
    parser.add_argument(
        "output_file",
        type=str,
        help="Path to save the transformed benchmark JSON file"
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation (default: 2)"
    )

    args = parser.parse_args()

    # Convert to Path objects
    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    # Check if input file exists
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist")
        sys.exit(1)

    # Load source data
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        print(f"Successfully loaded {len(source_data)} records from {input_path}")
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON from {input_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read file {input_path}: {e}")
        sys.exit(1)

    # Ensure source_data is a list
    if not isinstance(source_data, list):
        print("Error: Source data must be a JSON array")
        sys.exit(1)

    # Transform the data
    transformed_data = transform_benchmark_data(source_data)

    if not transformed_data:
        print("Warning: No records were successfully transformed")

    # Save the transformed data
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transformed_data, f, indent=args.indent, ensure_ascii=False)
        print(f"\nSuccessfully transformed {len(transformed_data)} records")
        print(f"Saved transformed data to '{output_path}'")
    except Exception as e:
        print(f"Error: Failed to write output file {output_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
