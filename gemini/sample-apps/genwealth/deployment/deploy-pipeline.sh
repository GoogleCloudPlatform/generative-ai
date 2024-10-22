#!/usr/bin/env bash

# Load env variables
source ./env.sh

# pubsub access for Cloud Function GCS trigger
echo "Adding function permissions"
SERVICE_ACCOUNT="$(gsutil kms serviceaccount -p "$PROJECT_ID")"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role='roles/pubsub.publisher'

# Create GCS buckets
echo "Creating GCS buckets"
gcloud storage buckets create gs://"${PROJECT_ID}"-docs --location="${REGION}" \
  --project="${PROJECT_ID}" --uniform-bucket-level-access

gcloud storage buckets create gs://"${PROJECT_ID}"-docs-metadata --location="${REGION}" \
  --project="${PROJECT_ID}" --uniform-bucket-level-access

gcloud storage buckets create gs://"${PROJECT_ID}"-doc-ai --location="${REGION}" \
  --project="${PROJECT_ID}" --uniform-bucket-level-access

# Create pubsub topic
echo "Creating pubsub topic"
gcloud pubsub topics create "${PROJECT_ID}"-doc-ready --project="${PROJECT_ID}"

# Create VPC connector for cloud function
echo "Creating VPC connector for cloud functions"
gcloud compute networks vpc-access connectors create vpc-connector --region="${REGION}" \
  --network=demo-vpc \
  --range=10.8.0.0/28 \
  --project="${PROJECT_ID}" \
  --machine-type=e2-micro

# Create Document AI processor
echo "Creating Document AI processor"
echo '{"type": "OCR_PROCESSOR","displayName": "document-text-extraction"}' >request.json
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d @request.json \
  "https://us-documentai.googleapis.com/v1/projects/${PROJECT_ID}/locations/us/processors"

DOC_AI_PROCESSOR_NAME=$(curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://us-documentai.googleapis.com/v1/projects/${PROJECT_ID}/locations/us/processors" |
  jq '.processors | .[] | select(.displayName=="document-text-extraction").name')

DOC_AI_PROCESSOR_ID=${DOC_AI_PROCESSOR_NAME##*/}
DOC_AI_PROCESSOR_ID=${DOC_AI_PROCESSOR_ID:0:-1}

# Create functions
# jscpd:ignore-start
echo "Creating Cloud Function: analyze-prospectus"
gcloud functions deploy analyze-prospectus \
  --gen2 \
  --region="${REGION}" \
  --runtime=python311 \
  --source="./function-scripts/analyze-prospectus" \
  --entry-point="analyze_prospectus" \
  --set-env-vars="REGION=${REGION},ZONE=${ZONE},PROJECT_ID=${PROJECT_ID}" \
  --set-secrets "ALLOYDB_PASSWORD=alloydb-password-${PROJECT_ID}:1" \
  --egress-settings=private-ranges-only \
  --vpc-connector=vpc-connector \
  --timeout=540s \
  --run-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --trigger-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --concurrency=1 \
  --max-instances=100 \
  --ingress-settings=all \
  --memory=2gi \
  --cpu=2000m \
  --trigger-topic="${PROJECT_ID}-doc-ready"

sleep 10

echo "Creating Cloud Function: write-metadata"
gcloud functions deploy write-metadata \
  --gen2 \
  --region="${REGION}" \
  --runtime=python311 \
  --source="./function-scripts/write-metadata" \
  --entry-point="write_metadata" \
  --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
  --timeout=60s \
  --run-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --trigger-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --concurrency=1 \
  --max-instances=100 \
  --ingress-settings=all \
  --memory=256Mi \
  --cpu=.5 \
  --trigger-bucket="${PROJECT_ID}-docs"

sleep 10

echo "Creating Cloud Function: process-pdf"
gcloud functions deploy process-pdf \
  --gen2 \
  --region="${REGION}" \
  --runtime=python311 \
  --source="./function-scripts/process-pdf" \
  --entry-point="process_pdf" \
  --set-env-vars="REGION=${REGION},ZONE=${ZONE},PROJECT_ID=${PROJECT_ID},PROCESSOR_ID=${DOC_AI_PROCESSOR_ID},IP_TYPE=private" \
  --set-secrets "ALLOYDB_PASSWORD=alloydb-password-${PROJECT_ID}:1" \
  --egress-settings=private-ranges-only \
  --vpc-connector=vpc-connector \
  --timeout=540s \
  --run-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --trigger-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --concurrency=1 \
  --max-instances=100 \
  --ingress-settings=all \
  --memory=2gi \
  --cpu=2000m \
  --trigger-bucket="${PROJECT_ID}-docs"

# jscpd:ignore-end
