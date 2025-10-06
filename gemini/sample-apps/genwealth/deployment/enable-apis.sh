#!/usr/bin/env bash

# Enable first batch of APIs (20 max per batch)
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
gcloud services enable iam.googleapis.com \
  compute.googleapis.com \
  storage-component.googleapis.com \
  pubsub.googleapis.com \
  cloudkms.googleapis.com \
  logging.googleapis.com \
  alloydb.googleapis.com \
  servicedirectory.googleapis.com \
  serviceusage.googleapis.com \
  networkmanagement.googleapis.com \
  cloudresourcemanager.googleapis.com \
  servicenetworking.googleapis.com \
  dns.googleapis.com \
  orgpolicy.googleapis.com \
  aiplatform.googleapis.com \
  cloudfunctions.googleapis.com \
  eventarc.googleapis.com \
  secretmanager.googleapis.com \
  vpcaccess.googleapis.com \
  documentai.googleapis.com --project "${PROJECT_ID}"

# Enable second batch of APIs
gcloud services enable run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  discoveryengine.googleapis.com --project "${PROJECT_ID}"
