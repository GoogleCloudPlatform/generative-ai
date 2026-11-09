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

# Deploy Wayfinder to Cloud Run.
#
# Secure by default: AUTH_ENABLED=true. The co-hosted demo pages keep working
# through the SELF_ORIGIN same-origin bypass; other sites need an API key.
# Set API_KEYS_SECRET=<secret-name> to mount API keys from Secret Manager.
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
# Cloud Run region for the service. Separate from GOOGLE_CLOUD_LOCATION (the
# Agent Platform location for model calls), which can be a multi-region like "us".
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-wayfinder}"

if [ -z "$PROJECT_ID" ]; then
  echo "Error: set GOOGLE_CLOUD_PROJECT or run 'gcloud config set project YOUR_PROJECT_ID'"
  exit 1
fi

echo "Deploying Wayfinder to Cloud Run: project=$PROJECT_ID region=$REGION service=$SERVICE_NAME"

from_env_file() {
  if [ -f .env ]; then grep "^$1=" .env | tail -n1 | cut -d '=' -f2- || true; fi
}

EMPTY_JSON='{}'
VERTEX_LOCATION="${GOOGLE_CLOUD_LOCATION:-$(from_env_file GOOGLE_CLOUD_LOCATION)}"
VERTEX_LOCATION="${VERTEX_LOCATION:-us}"
VERTEX_SEARCH_ENGINES="${VERTEX_SEARCH_ENGINES:-$(from_env_file VERTEX_SEARCH_ENGINES)}"
[ -z "${VERTEX_SEARCH_ENGINES}" ] && VERTEX_SEARCH_ENGINES="$EMPTY_JSON"
API_KEYS="${API_KEYS:-$EMPTY_JSON}"
GEMINI_MODEL="${GEMINI_MODEL:-$(from_env_file GEMINI_MODEL)}"
GEMINI_FALLBACK_MODEL="${GEMINI_FALLBACK_MODEL:-$(from_env_file GEMINI_FALLBACK_MODEL)}"
GEMINI_TEXT_MODEL="${GEMINI_TEXT_MODEL:-$(from_env_file GEMINI_TEXT_MODEL)}"

SELF_ORIGIN=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" \
  --format "value(status.url)" 2>/dev/null | sed 's|https://||' || echo "")

# Env vars go through a YAML file so JSON values (commas, braces) are safe.
ENV_FILE="$(mktemp)"
trap 'rm -f "$ENV_FILE"' EXIT
{
  echo "GOOGLE_CLOUD_PROJECT: '${PROJECT_ID}'"
  echo "GOOGLE_CLOUD_LOCATION: '${VERTEX_LOCATION}'"
  echo "VERTEX_SEARCH_ENGINES: '${VERTEX_SEARCH_ENGINES}'"
  echo "AUTH_ENABLED: '${AUTH_ENABLED:-true}'"
  echo "SELF_ORIGIN: '${SELF_ORIGIN}'"
  echo "ALLOWED_ORIGINS: '${ALLOWED_ORIGINS:-*}'"
  [ -n "${GEMINI_MODEL}" ] && echo "GEMINI_MODEL: '${GEMINI_MODEL}'"
  [ -n "${GEMINI_FALLBACK_MODEL}" ] && echo "GEMINI_FALLBACK_MODEL: '${GEMINI_FALLBACK_MODEL}'"
  [ -n "${GEMINI_TEXT_MODEL}" ] && echo "GEMINI_TEXT_MODEL: '${GEMINI_TEXT_MODEL}'"
  for v in LIVE_VOICE LIVE_PROACTIVE_AUDIO LIVE_AFFECTIVE_DIALOG LIVE_CONTEXT_COMPRESSION LIVE_ASYNC_SEARCH; do
    [ -n "${!v:-}" ] && echo "${v}: '${!v}'"
  done
  [ -z "${API_KEYS_SECRET:-}" ] && echo "API_KEYS: '${API_KEYS}'"
  true
} > "$ENV_FILE"

SECRET_ARGS=()
[ -n "${API_KEYS_SECRET:-}" ] && SECRET_ARGS=(--set-secrets "API_KEYS=${API_KEYS_SECRET}:latest")

# --allow-unauthenticated: end users' browsers load the widget, so Cloud Run
# IAM can't gate it. Access control is AUTH_ENABLED (API key + Origin).
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated \
  --env-vars-file "$ENV_FILE" \
  "${SECRET_ARGS[@]}" \
  --session-affinity \
  --min-instances 1 \
  --memory 512Mi \
  --timeout 3600

NEW_ORIGIN=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" \
  --format "value(status.url)" | sed 's|https://||')
if [ "$SELF_ORIGIN" != "$NEW_ORIGIN" ]; then
  echo "Updating SELF_ORIGIN to $NEW_ORIGIN..."
  gcloud run services update "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" \
    --update-env-vars "SELF_ORIGIN=$NEW_ORIGIN"
fi

echo ""
echo "Deployed: https://$NEW_ORIGIN"
echo "  Personas:  https://$NEW_ORIGIN/"
echo "  Widget:    <script src=\"https://$NEW_ORIGIN/wayfinder.js\" data-key=\"wf_...\"></script>"
