#!/usr/bin/env bash

# Load env variables
source ./env.sh

# Update the index
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/0/documents:import" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'${DOCS_METADATA_BUCKET}'/*.jsonl"],
      "dataSchema": "document",
    }
  }'
