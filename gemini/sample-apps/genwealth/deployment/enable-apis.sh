#!/usr/bin/env bash

# Enable Backend APIs
echo "Enabling APIs"
PROJECT_ID=$(gcloud config get-value project 2> /dev/null)
gcloud services enable iam.googleapis.com --project "${PROJECT_ID}"
gcloud services enable compute.googleapis.com --project "${PROJECT_ID}"
gcloud services enable storage-component.googleapis.com --project "${PROJECT_ID}"
gcloud services enable pubsub.googleapis.com --project "${PROJECT_ID}"
gcloud services enable cloudkms.googleapis.com --project "${PROJECT_ID}"
gcloud services enable logging.googleapis.com --project "${PROJECT_ID}"
gcloud services enable alloydb.googleapis.com --project "${PROJECT_ID}"
gcloud services enable servicedirectory.googleapis.com --project "${PROJECT_ID}"
gcloud services enable serviceusage.googleapis.com --project "${PROJECT_ID}"
gcloud services enable networkmanagement.googleapis.com --project "${PROJECT_ID}"
gcloud services enable cloudresourcemanager.googleapis.com --project "${PROJECT_ID}"
gcloud services enable servicenetworking.googleapis.com --project "${PROJECT_ID}"
gcloud services enable dns.googleapis.com --project "${PROJECT_ID}"
gcloud services enable orgpolicy.googleapis.com --project "${PROJECT_ID}"
gcloud services enable aiplatform.googleapis.com --project "${PROJECT_ID}"

# Enable pipeline APIs
gcloud services enable cloudfunctions.googleapis.com --project "${PROJECT_ID}"
gcloud services enable eventarc.googleapis.com --project "${PROJECT_ID}"
gcloud services enable secretmanager.googleapis.com --project "${PROJECT_ID}"
gcloud services enable vpcaccess.googleapis.com --project "${PROJECT_ID}"
gcloud services enable documentai.googleapis.com --project "${PROJECT_ID}"

# Enable front end APIs
gcloud services enable run.googleapis.com --project "${PROJECT_ID}"
gcloud services enable artifactregistry.googleapis.com --project "${PROJECT_ID}"
gcloud services enable cloudbuild.googleapis.com --project "${PROJECT_ID}"