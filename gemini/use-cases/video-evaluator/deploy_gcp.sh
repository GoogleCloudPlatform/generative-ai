#!/bin/bash
# Copyright 2026 Google LLC
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


# Generative AI Video Evaluator Cloud Run Deployment Script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Absolute path to gcloud found on system
GCLOUD_BIN="/Users/moshem/gcloud --version/google-cloud-sdk/bin/gcloud"
export CLOUDSDK_PYTHON="/usr/local/bin/python3.13"

echo "------------------------------------------------"
echo -e "${BLUE}🚀 Starting Generative AI Video Evaluator Deployment to Cloud Run...${NC}"
echo -e "${BLUE}🐍 Using Python: ${GREEN}$($CLOUDSDK_PYTHON --version)${NC}"
echo "------------------------------------------------"

# Check for gcloud
if ! [ -f "$GCLOUD_BIN" ]; then
  # Fallback to standard path if found
  if [ -x "$(command -v gcloud)" ]; then
    GCLOUD_BIN="gcloud"
  else
    echo -e "${RED}❌ Error: gcloud CLI not found at $GCLOUD_BIN${NC}"
    echo "Please install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
  fi
fi

# Utility function to run gcloud
run_gcloud() {
  "$GCLOUD_BIN" "$@"
}

# Get current project
PROJECT_ID=$(run_gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo -e "${RED}❌ Error: No Google Cloud project is configured.${NC}"
  echo "Please run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo -e "${BLUE}📦 Using Project: ${GREEN}$PROJECT_ID${NC}"

# Enable necessary services
echo -e "${BLUE}🔧 Ensuring necessary APIs are enabled (this may take a moment)...${NC}"
run_gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --quiet

# Deploy to Cloud Run
echo -e "${BLUE}🏗️ Building and deploying to Cloud Run...${NC}"
run_gcloud run deploy genai-video-eval \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 1

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✅ Deployment successful!${NC}"
  echo -e "${BLUE}📍 Service URL: ${NC}$(run_gcloud run services describe genai-video-eval --region us-central1 --format='value(status.url)')"
else
  echo -e "${RED}❌ Deployment failed. Check the logs above for details.${NC}"
  exit 1
fi
