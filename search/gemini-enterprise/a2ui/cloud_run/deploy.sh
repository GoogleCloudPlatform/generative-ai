#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
if [[ "$#" -lt 2 ]]; then
    echo "Usage: $0 <PROJECT_ID> <SERVICE_NAME> [MODEL_NAME]"
    echo "MODEL_NAME can be 'gemini-2.5-pro' or 'gemini-2.5-flash' (default)."
    exit 1
fi

PROJECT_ID=$1
SERVICE_NAME=$2
MODEL_NAME=${3:-"gemini-2.5-flash"}

# Validate model name
if [[ "$MODEL_NAME" != "gemini-2.5-pro" && "$MODEL_NAME" != "gemini-2.5-flash" ]]; then
    echo "Invalid model name. Please use 'gemini-2.5-pro' or 'gemini-2.5-flash'."
    exit 1
fi

# The region to deploy to
REGION="us-central1"

# The memory to allocate to the service
MEMORY="1Gi"

# --- Deployment ---

echo "Starting deployment of service '$SERVICE_NAME' to project '$PROJECT_ID' in region '$REGION' with model '$MODEL_NAME'..."

# Deploy to Cloud Run from source code
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --memory "$MEMORY" \
  --no-allow-unauthenticated \
  --set-env-vars=GOOGLE_CLOUD_PROJECT="$PROJECT_ID",GOOGLE_CLOUD_LOCATION="$REGION",GOOGLE_GENAI_USE_VERTEXAI=TRUE,MODEL="$MODEL_NAME"


echo "Deployment complete."
echo "Service URL: $(gcloud run services describe "$SERVICE_NAME" \
  --platform managed \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format 'value(status.url)')"

# After the initial deployment, get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format='value(status.url)')

# Update the service to set the AGENT_URL environment variable
echo "Updating service with its public URL: $SERVICE_URL"
gcloud run services update "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --update-env-vars=AGENT_URL="$SERVICE_URL"


echo "Deployment Complete!"
echo "Agent URL: ${SERVICE_URL}"
