#!/usr/bin/env bash

# Load env variables
source ./env.sh

# Update the Vertex AI configId
read -r -p "Enter the Vertex AI configId: " SEARCH_CONFIG_ID
echo "export SEARCH_CONFIG_ID=${SEARCH_CONFIG_ID}" >>env.sh

#
# Create the Artifact Registry repository:
#
echo "Creating the Artifact Registry repository"
gcloud artifacts repositories create genwealth \
  --repository-format=docker \
  --location="$REGION" \
  --project="$PROJECT_ID"

# Make PDFs publically viewable
gcloud storage buckets add-iam-policy-binding gs://${PROJECT_ID}-docs \
  --member=allUsers --role=roles/storage.objectViewer
