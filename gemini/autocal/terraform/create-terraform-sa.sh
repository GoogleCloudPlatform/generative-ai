#!/bin/bash
#
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

# create-terraform-sa.sh
#
# This script creates a terraform service account that can be used to deploy.
# Over-engineered, but taken from another project that did a lot more.

# Print information to stdout
info() {
  echo '[Info]' "$@"
}

# Print a warning to stderr
warning() {
  echo >&2 '[Warning]' "$@"
}

# Print an error to stderr and stop
error() {
  echo >&2 '[Error]' "$@"
  exit 1
}

# Checks if a command exists and halts with a fatal error if it does not
# Usage:
# check_cmd <cmd_name>
# e.g.
# check_cmd jq
check_cmd() {
  if ! command -v "$@" >/dev/null 2>&1; then
    error Command "$@" not found - please install it
  fi
}

apis=(
  "cloudresourcemanager.googleapis.com"
)

if [[ -z "${PROJECT_ID}" ]]; then
  error Expected PROJECT_ID environment variable
fi

if [[ -z "${TERRAFORM_SA_NAME}" ]]; then
  TERRAFORM_SA_NAME=terraform-builder
  info "Setting default TERRAFORM_SA_NAME to ${TERRAFORM_SA_NAME}"
fi

if [[ -z "${TERRAFORM_ORG_POLICY}" ]]; then
  TERRAFORM_ORG_POLICY=true
  info "Setting default TERRAFORM_ORG_POLICY to ${TERRAFORM_ORG_POLICY}"
fi

main() {
  check_cmd gcloud
  info "Creating Service Account: ${TERRAFORM_SA_NAME}"
  # Check if SA exists
  if gcloud iam service-accounts describe "${TERRAFORM_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    info "Service account ${TERRAFORM_SA_NAME} already exists - continuing"
  else
    gcloud iam service-accounts create "${TERRAFORM_SA_NAME}" --project "${PROJECT_ID}" >/dev/null
  fi

  info "Enabling APIs:" "${apis[@]}"
  gcloud services enable "${apis[@]}" --project "${PROJECT_ID}" >/dev/null

  # Grant terraform SA broad rights
  build_roles=(roles/iam.serviceAccountUser roles/owner)
  info "Binding Build Project roles to SA:" "${build_roles[@]}"
  for role in "${build_roles[@]}"; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${TERRAFORM_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --role="${role}" --condition=None >/dev/null
  done
  if [[ "${TERRAFORM_ORG_POLICY,,}" = true ]]; then
    ORG_ID="$(gcloud projects get-ancestors "${PROJECT_ID}" | grep organization | awk '{print $1}')"
    org_roles=(roles/orgpolicy.policyAdmin)
    for role in "${org_roles[@]}"; do
      gcloud organizations add-iam-policy-binding "${ORG_ID}" --member="serviceAccount:${TERRAFORM_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --role="${role}" --condition=None >/dev/null
    done
  fi

  me="$(gcloud config list account --format "value(core.account)")"
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="user:${me}" --role="roles/iam.serviceAccountTokenCreator" --condition=None >/dev/null
  info Complete. Before running terraform set your impersonate environment variable:
  echo 'export GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="'"${TERRAFORM_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"'"'
}

main
