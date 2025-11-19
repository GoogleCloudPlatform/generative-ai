# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#!/bin/bash

# IMPORTANT: Before running this script, ensure you have:
# 1. Authenticated with gcloud: `gcloud auth login`
# 2. Configured Docker for Artifact Registry: `gcloud auth configure-docker`
# 3. Replaced [YOUR_PROJECT_ID] and [YOUR_GEMINI_API_KEY] below.

# --- Step 1: Build and Push the Container Image ---
# Replace [YOUR_PROJECT_ID] with your Google Cloud Project ID
PROJECT_ID=[YOUR_PROJECT_ID]

# Generate a unique tag based on the current time (Forces a fresh pull)
# --- Step 2: Deploy to Cloud Run ---


SERVICE_NAME="gemini-live-health" # Cloud Run service name
REGION="us-central1"              # Cloud Run region

SERVICE_URL="" # Will be Updated with your deployed service URL after first deployment

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${TIMESTAMP}"

echo "Building and pushing container image: ${IMAGE_NAME}"
gcloud builds submit --tag "${IMAGE_NAME}" --no-cache

if [ $? -ne 0 ]; then
  echo "Container build failed. Exiting."
  exit 1
fi



echo "Deploying service ${SERVICE_NAME} to Cloud Run in ${REGION}"
DEPLOY_OUTPUT=$(gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --min-instances=1 \
  --timeout=3600 \
  --memory=2Gi \
  --session-affinity \
  --concurrency=1 \
  --cpu=2 \
  --no-cpu-throttling \
  --set-env-vars="SERVICE_URL=${SERVICE_URL}" \
  --format="value(status.url)")

if [ $? -ne 0 ]; then
  echo "Cloud Run deployment failed. Exiting."
  exit 1
fi

echo "Updating service with its own public URL..."
gcloud run services update "${SERVICE_NAME}" \
  --region "${REGION}" \
  --update-env-vars="SERVICE_URL=${DEPLOY_OUTPUT}"

if [ $? -ne 0 ]; then
  echo "Failed to update service with its public URL. Exiting."
  exit 1
fi


# The SERVICE_URL is now directly set in the deployment command.
# The DEPLOY_OUTPUT still contains the full URL, which is useful for Twilio configuration.

echo "Service deployed to: ${DEPLOY_OUTPUT}"
echo "Deployment script completed successfully!"
echo "Next steps:"
echo "1. Copy the Service URL: ${DEPLOY_OUTPUT}"
echo "2. Go to your Twilio phone number configuration in the Twilio Console."
echo "3. Set the 'A CALL COMES IN' webhook to: ${DEPLOY_OUTPUT}/twiml (HTTP POST)"
echo "4. Save the Twilio configuration and make a test call!"
