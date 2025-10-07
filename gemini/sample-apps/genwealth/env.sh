#!/usr/bin/env bash

# Update env variables here
export REGION="us-central1"
export ZONE="us-central1-a"
export LOCAL_IPV4="X.X.X.X"

# Keep all defaults below
# shellcheck disable=SC2155
export PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
export ALLOYDB_CLUSTER="alloydb-cluster"
export ALLOYDB_INSTANCE="alloydb-instance"
# shellcheck disable=SC2155
export ALLOYDB_IP=$(gcloud alloydb instances describe $ALLOYDB_INSTANCE --cluster=$ALLOYDB_CLUSTER --region=$REGION --view=BASIC --format=json 2>/dev/null | jq -r .ipAddress)
# shellcheck disable=SC2155
export ALLOYDB_PASSWORD=$(gcloud secrets versions access latest --secret="alloydb-password-$PROJECT_ID")
export PGADMIN_USER="demouser@genwealth.com"
# shellcheck disable=SC2155
export PGADMIN_PASSWORD=$(gcloud secrets versions access latest --secret="pgadmin-password-$PROJECT_ID")
export PGPORT=5432
export PGDATABASE=ragdemos
export PGUSER=postgres
export PGHOST=${ALLOYDB_IP}
export PGPASSWORD=${ALLOYDB_PASSWORD}
export PROSPECTUS_BUCKET=${PROJECT_ID}-docs # GCS Bucket for storing pro
export VPC_NETWORK=demo-vpc
export VPC_SUBNET=$VPC_NETWORK
export VPC_NAME=$VPC_NETWORK
# shellcheck disable=SC2155
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export GCE_INSTANCE="pgadmin"
# shellcheck disable=SC2155
export ORGANIZATION=$(gcloud projects get-ancestors ${PROJECT_ID} --format=json | jq -r '.[] | select(.type == "organization").id')
export DOCS_BUCKET=${PROJECT_ID}-docs
export DOCS_METADATA_BUCKET=${PROJECT_ID}-docs-metadata
export DOC_AI_BUCKET=${PROJECT_ID}-doc-ai
DATASTORE_ID=$(curl -s -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/dataStores" | jq -r '.dataStores | .[] | select(.displayName=="search-prospectus").name' 2>/dev/null)
export DATASTORE_ID=${DATASTORE_ID##*/}
export DATA_STORE_ID=${DATASTORE_ID}
