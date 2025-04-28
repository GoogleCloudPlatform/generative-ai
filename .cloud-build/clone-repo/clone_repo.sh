#!/bin/bash

# Reads the destination GCS URI from the OUTPUT_URI file.
OUTPUT_URI=$(cat OUTPUT_URI)

# Clones the generative-ai repository from GitHub.
git clone https://github.com/GoogleCloudPlatform/generative-ai.git

# Changes the current directory to the cloned repository.
cd generative-ai

# Copies the specified directory to the destination GCS URI using gsutil.
gsutil -m cp -r . $OUTPUT_URI/generative-ai/gemini/getting-started/
