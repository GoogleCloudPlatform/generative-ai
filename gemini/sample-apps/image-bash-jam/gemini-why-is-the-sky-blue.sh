#!/bin/bash

# first: gcloud auth login

# Verbs:
# generateContent (used to work in staging, doesnt work in prod)
# streamGenerateContent (works in PROD)

MODEL_ID="gemini-pro"
LOCATION="us-central1"
TMP_OUTPUT_FILE=".tmp.why-sky-blue.json"
JQ_PATH_PLURAL=".[].candidates[0].content.parts[0].text" # PROD_URL_SELECTOR all answers from StreamGenerateContent

. .envrc

set -euo pipefail

gcloud config set project "$PROJECT_ID"

# PROD_URL="https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/$MODEL_ID:streamGenerateContent"

curl -X POST \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json"  \
    https://us-central1-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL_ID}:streamGenerateContent -d \
    $'{
      "contents": {
        "role": "USER",
        "parts": { "text": "Why is the sky blue?" }
      }
    }'  1>"$TMP_OUTPUT_FILE" 2>/dev/null

CLEANED_OUTPUT="$(jq -r "$JQ_PATH_PLURAL" < "$TMP_OUTPUT_FILE" | xargs -0 )"

echo "# ♊ Input: 'Why is the sky blue?'"
echo "# ♊ Output: '$CLEANED_OUTPUT'"
