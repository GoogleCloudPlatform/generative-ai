#!/usr/bin/env bash

# Load env variables
source ./env.sh

# Enable APIs
echo "Enabling discovery engine API"
gcloud services enable discoveryengine.googleapis.com --project "${PROJECT_ID}"

# Call the first API with yes to enable to second necessary API (can't do this directly today)

# Create S&C Datastore (pdf + jsonl metadata)
yes | curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores?dataStoreId=search-prospectus-${PROJECT_ID}" \
  -d '{
  "displayName": "search-prospectus",
  "industryVertical": "GENERIC",
  "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
  "contentConfig": "CONTENT_REQUIRED",
  "documentProcessingConfig": {
    "defaultParsingConfig": {
      "ocrParsingConfig": {
        "useNativeText": "false"
      }
    }
  }
}'

echo "Waiting 70 seconds for data store."
sleep 70

# Upload samples to gcs
gsutil -m cp gs://github-repo/generative-ai/sample-apps/genwealth/sample-prospectus/*.pdf gs://"${DOCS_BUCKET}"

sleep 30

# Get the data store id
DATA_STORE_ID=$(curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores" | jq -r '.dataStores | .[] | select(.displayName=="search-prospectus").name')
DATA_STORE_ID=${DATA_STORE_ID##*/}

sleep 10

# Import data from gcs
# Ref: https://cloud.google.com/generative-ai-app-builder/docs/create-data-store-es#cloud-storage
# Important: Specify the metadata bucket in the gcsSource config, NOT the bucket with the source pdf's. The metadata in the jsonl files will point to the associated pdf.
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/0/documents:import" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'"${DOCS_METADATA_BUCKET}"'/*.jsonl"],
      "dataSchema": "document",
    }
  }'

# Create S&C App
# Ref: https://cloud.google.com/generative-ai-app-builder/docs/create-engine-es
# Note: Faceted search for the widget has to be enabled manually in the console as of today.
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines?engineId=search-prospectus-${PROJECT_ID}" \
  -d '{
  "displayName": "search-prospectus",
  "dataStoreIds": ["'"${DATA_STORE_ID}"'"],
  "solutionType": "SOLUTION_TYPE_SEARCH",
  "searchEngineConfig": {
    "searchTier": "SEARCH_TIER_ENTERPRISE",
    "searchAddOns": ["SEARCH_ADD_ON_LLM"]
  }
}'

echo "Deploying function: update-search-index"
gcloud functions deploy update-search-index \
  --gen2 \
  --region="${REGION}" \
  --runtime=python311 \
  --source="./function-scripts/update-search-index" \
  --entry-point="update_search_index" \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},DATASTORE_ID=${DATA_STORE_ID},DOCS_METADATA_BUCKET=${DOCS_METADATA_BUCKET}" \
  --timeout=540s \
  --run-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --trigger-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --concurrency=1 \
  --max-instances=100 \
  --ingress-settings=all \
  --memory=256Mi \
  --cpu=.5 \
  --trigger-bucket="${PROJECT_ID}-docs-metadata"
