#!/bin/bash

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Builds and deploys the entity extraction service to Cloud Run.
#

# Exit immediately if a command fails, treat unset variables as an error, and cause
# pipelines to fail if any command within them fails.
set -euo pipefail

# Load environment variables from .env file.
if [ -f .env ]; then
  echo "Loading environment variables from .env"
  set -o allexport
  source .env
  set +o allexport
else
  echo ".env file not found. Please create one."
  exit 1
fi

# Enable APIs.
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Submit build to Artifact Registry.
gcloud builds submit --tag gcr.io/$CLOUD_RUN_PROJECT_ID/$SERVICE_NAME

# Deploy service.
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$CLOUD_RUN_PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $CLOUD_RUN_REGION
