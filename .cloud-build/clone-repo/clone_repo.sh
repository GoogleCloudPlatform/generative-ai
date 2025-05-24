#!/bin/bash

# Reads the destination GCS URI from the OUTPUT_URI file.
OUTPUT_URI=$(cat OUTPUT_URI)

# Clones the generative-ai repository from GitHub.
git clone --depth 1 -b main https://github.com/GoogleCloudPlatform/generative-ai.git

# Changes the current directory to the cloned repository.
cd generative-ai || exit 1

# Enable globstar for recursive globbing (e.g., **/*.ipynb)
# This allows '**' to match directories and subdirectories recursively.
shopt -s globstar

# Copies only .ipynb files from the current directory and its subdirectories
# to the destination GCS URI, under a 'generative-ai' prefix.
# The '-m' option runs parallel copies for faster transfer.
# The '**/*.ipynb' glob will expand to all .ipynb files found recursively.
# gsutil will preserve the relative path structure of the copied files under
# the specified destination prefix.
gsutil -m cp ./**/*.ipynb "$OUTPUT_URI/generative-ai/"
