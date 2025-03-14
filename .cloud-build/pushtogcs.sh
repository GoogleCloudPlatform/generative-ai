#!/bin/bash

OUTPUT_URI=$(cat OUTPUT_URI)

for filename in /workspace/generative-ai/gemini/getting-started/*.ipynb; 
do
  name=$(basename "$filename")
  gcloud storage cp "$filename" $OUTPUT_URI/generative-ai/gemini/getting-started/"$name"
done