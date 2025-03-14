#!/bin/bash

OUTPUT_URI=$(cat OUTPUT_URI)

git clone https://github.com/GoogleCloudPlatform/generative-ai.git

cd generative-ai

gsutil -m cp -r . $OUTPUT_URI/generative-ai/gemini/getting-started/