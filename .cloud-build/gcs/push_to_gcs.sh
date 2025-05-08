#!/bin/bash

OUTPUT_URI=$(cat OUTPUT_URI)

find /workspace/generative-ai/ -name "*.ipynb" -print0 | while IFS= read -r -d $'\0' filename; do
  # Calculate the relative path from /workspace/
  relative_path="${filename/\/workspace\//}"
  # Copy the file to GCS, preserving the directory structure
  gcloud storage cp "$filename" "$OUTPUT_URI/$relative_path"
done
