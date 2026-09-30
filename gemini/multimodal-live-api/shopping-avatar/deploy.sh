#!/bin/bash
set -e

# --- Error Handler ---
error_handler() {
  local exit_code=$?
  local line_num=$1
  echo ""
  echo "❌ ERROR: Deployment failed at line $line_num with exit code $exit_code"
  exit $exit_code
}
trap 'error_handler $LINENO' ERR

# --- Configuration & Dynamic Discovery ---
# 1. Project ID: use $PROJECT_ID, or fall back to active gcloud config
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [ -z "$PROJECT_ID" ]; then
  echo "❌ ERROR: No Google Cloud project specified. Set PROJECT_ID or run: gcloud config set project <PROJECT_ID>"
  exit 1
fi

# 2. Region: use $REGION, or active gcloud run/region, or default to us-central1
REGION="${REGION:-$(gcloud config get-value run/region 2>/dev/null)}"
REGION="${REGION:-us-central1}"

# 3. Service Name: customizable with default
SERVICE_NAME="${SERVICE_NAME:-cymbal-avatar}"

# 4. Optional Service Account & Impersonation
DEPLOY_ARGS=()
if [ -n "$SERVICE_ACCOUNT" ]; then
  DEPLOY_ARGS+=(--service-account "$SERVICE_ACCOUNT")
fi
if [ -n "$IMPERSONATE_SERVICE_ACCOUNT" ]; then
  DEPLOY_ARGS+=(--impersonate-service-account "$IMPERSONATE_SERVICE_ACCOUNT")
fi

# 5. Parse backend .env for any additional custom variables
ENV_VARS=""
if [ -f "ecommerce/backend/.env" ]; then
  echo "📄 Found backend/.env, parsing variables..."
  ENV_VARS=$(grep -v '^#' ecommerce/backend/.env | grep -v '^$' | \
    grep -v '^GOOGLE_CLOUD_PROJECT=' | \
    grep -v '^GOOGLE_CLOUD_LOCATION=' | \
    grep -v '^VERTEX_PROJECT_ID=' | \
    grep -v '^VERTEX_LOCATION=' | \
    grep -v '^MULTIMODAL_EMBEDDING_LOCATION=' | \
    tr -d '\r' | paste -s -d "," -)
fi

echo "🚀 Deploying ${SERVICE_NAME} to Cloud Run..."
echo "   Project: ${PROJECT_ID}"
echo "   Region:  ${REGION}"

gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --min-instances 1 \
  --no-cpu-throttling \
  "${DEPLOY_ARGS[@]}" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},VERTEX_PROJECT_ID=${PROJECT_ID},VERTEX_LOCATION=${REGION},MULTIMODAL_EMBEDDING_LOCATION=global${ENV_VARS:+,}${ENV_VARS}"

echo "🎉 Deployment completed successfully!"

