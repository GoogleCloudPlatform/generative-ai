#!/usr/bin/env bash
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
#
# Deploy Rosetta as a single container to Cloud Run (gen2).
# The image carries python 3.12 + git + uv + agents-cli + the app, and runs
# serve.py (which shells out to that toolchain and spawns a child adk api_server).
#
# The deployed service talks to Gemini Enterprise Agent Platform as its own service account, so no API
# key is involved.
#
# Usage:
#   PROJECT=my-project bash scripts/deploy.sh
#   PROJECT=my-project REGION=europe-west1 bash scripts/deploy.sh
#
# Roles needed by whoever runs this:
#   roles/run.admin, roles/artifactregistry.admin, roles/iam.serviceAccountAdmin,
#   roles/iam.serviceAccountUser, roles/resourcemanager.projectIamAdmin
#
# NOTE: this uses plain `gcloud run deploy` rather than `agents-cli deploy`,
# because agents-cli injects a comma-separated ALLOW_ORIGINS value that collides
# with the commas in `--set-env-vars` and corrupts the env block.
#
# The service is deployed WITHOUT public access (--no-allow-unauthenticated).
# Grant yourself access after deploying, e.g.
#   gcloud run services add-iam-policy-binding rosetta --region=REGION \
#     --member=user:you@example.com --role=roles/run.invoker
set -euo pipefail

PROJECT="${PROJECT:?Set PROJECT to your Google Cloud project id}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-rosetta}"
SA="rosetta-sa@${PROJECT}.iam.gserviceaccount.com"
IMAGE="${IMAGE:-${REGION}-docker.pkg.dev/${PROJECT}/rosetta/${SERVICE}:latest}"

echo ">> 1/7 enable APIs on $PROJECT"
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project="$PROJECT"

echo ">> 2/7 service account ($SA)"
gcloud iam service-accounts create rosetta-sa --project="$PROJECT" \
  --display-name="Rosetta (Cloud Run)" 2>/dev/null || echo "   (exists)"

echo ">> 3/7 let the service account call Gemini Enterprise Agent Platform"
# --condition=None is required in non-interactive mode when the project's IAM
# policy already contains conditional bindings.
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${SA}" --role="roles/aiplatform.user" --condition=None >/dev/null

echo ">> 4/7 Artifact Registry repo (rosetta @ $REGION)"
gcloud artifacts repositories create rosetta --repository-format=docker \
  --location="$REGION" --project="$PROJECT" 2>/dev/null || echo "   (exists)"

echo ">> 5/7 build image ($IMAGE)"
gcloud builds submit --project="$PROJECT" --region="$REGION" \
  --config=deployment/cloudbuild.yaml --substitutions=_IMAGE="$IMAGE" .

echo ">> 6/7 deploy to Cloud Run"
gcloud run deploy "$SERVICE" \
  --project="$PROJECT" \
  --region="$REGION" \
  --image="$IMAGE" \
  --service-account="$SA" \
  --no-allow-unauthenticated \
  --execution-environment=gen2 \
  --memory=8Gi \
  --cpu=4 \
  --no-cpu-throttling \
  --min-instances=1 \
  --max-instances=1 \
  --concurrency=4 \
  --timeout=1800 \
  --set-env-vars=GOOGLE_CLOUD_PROJECT="$PROJECT",GOOGLE_CLOUD_LOCATION=global,ROSETTA_BACKEND=agent-platform,ROSETTA_WORKSPACE=/tmp/rosetta-workspace

echo ">> 7/7 done"
URL="$(gcloud run services describe "$SERVICE" --region="$REGION" \
  --project="$PROJECT" --format='value(status.url)')"
echo "Rosetta URL: ${URL}"
echo
echo "The service is private. Grant yourself access with:"
echo "  gcloud run services add-iam-policy-binding $SERVICE --region=$REGION \\"
echo "    --project=$PROJECT --member=user:YOUR_EMAIL --role=roles/run.invoker"
echo "then open it with an identity token, or put your own auth in front of it."
