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

# Provision the Google Cloud resources that Project Chrysalis's Agent Platform edition integrates with.
#
#   * BigQuery dataset  `chimera_telemetry` + table `recorded_requests` (Dream-RSI SQL counterfactual sweeps)
#   * Cloud KMS key ring `chimera-governance-ring` + asymmetric signing key `chimera-patch-signer`
#     (RSA_SIGN_PSS_2048_SHA256) used to sign Gemini-synthesized hotpatches and distilled principles
#   * Required APIs (Agent Platform, BigQuery, Cloud KMS, Cloud Logging)
#
# The script is idempotent (existing resources are left untouched) and asks for confirmation.
#
# Usage:  scripts/setup_gcp.sh [--yes]
#   GOOGLE_CLOUD_PROJECT   project to use (default: gcloud's configured project)
#   CHRYSALIS_BQ_LOCATION    BigQuery dataset location (default: US)
#   CHRYSALIS_KMS_LOCATION   Cloud KMS location (default: us-central1; must match app/config.py KMS_LOCATION)
#
# Cost / lifecycle notes:
#   * A software-protected asymmetric KMS key version costs ~USD 0.06/month plus ~USD 0.03 per 10k signatures.
#   * Cloud KMS key rings and keys can NOT be deleted (only key versions can be destroyed); see
#     scripts/teardown_gcp.sh, which destroys the key version and removes the BigQuery dataset.
#   * BigQuery storage for demo traces is a few KB; load jobs are free, queries scan < 1 MB per sweep.
set -euo pipefail

ASSUME_YES=false
[[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]] && ASSUME_YES=true

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
BQ_LOCATION="${CHRYSALIS_BQ_LOCATION:-US}"
DATASET="${CHRYSALIS_BQ_DATASET:-chimera_telemetry}"
TABLE="recorded_requests"
KMS_LOCATION="${CHRYSALIS_KMS_LOCATION:-us-central1}"
KEY_RING="chimera-governance-ring"
KEY_NAME="chimera-patch-signer"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: no project. Set GOOGLE_CLOUD_PROJECT or run 'gcloud config set project <id>'." >&2
  exit 1
fi

cat <<EOF
Project Chrysalis - Google Cloud provisioning plan
  Project            : ${PROJECT_ID}
  APIs               : aiplatform, bigquery, cloudkms, logging (enabled if needed)
  BigQuery           : ${PROJECT_ID}:${DATASET}.${TABLE}  (location ${BQ_LOCATION})
  Cloud KMS key      : projects/${PROJECT_ID}/locations/${KMS_LOCATION}/keyRings/${KEY_RING}/cryptoKeys/${KEY_NAME}
                       purpose=asymmetric-signing, algorithm=rsa-sign-pss-2048-sha256, protection=software
  NOTE: KMS key rings/keys are permanent (cannot be deleted). Key version ~USD 0.06/month.
EOF

if [[ "${ASSUME_YES}" != true ]]; then
  read -r -p "Proceed? [y/N] " reply
  [[ "${reply}" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

echo "==> Enabling APIs"
gcloud services enable aiplatform.googleapis.com bigquery.googleapis.com cloudkms.googleapis.com logging.googleapis.com \
  --project "${PROJECT_ID}"

echo "==> BigQuery dataset ${DATASET}"
if bq --project_id="${PROJECT_ID}" show --format=none "${PROJECT_ID}:${DATASET}" >/dev/null 2>&1; then
  echo "    exists"
else
  bq --project_id="${PROJECT_ID}" --location="${BQ_LOCATION}" mk --dataset \
    --description "Project Chrysalis Dream-RSI request traces" "${PROJECT_ID}:${DATASET}"
fi

echo "==> BigQuery table ${DATASET}.${TABLE}"
if bq --project_id="${PROJECT_ID}" show --format=none "${PROJECT_ID}:${DATASET}.${TABLE}" >/dev/null 2>&1; then
  echo "    exists"
else
  bq --project_id="${PROJECT_ID}" mk --table \
    --description "Recorded checkout request traces per demo run (run_id)" \
    "${PROJECT_ID}:${DATASET}.${TABLE}" \
    run_id:STRING,seq_id:INT64,timestamp:STRING,request_id:STRING,endpoint:STRING,status_code:INT64,latency_ms:FLOAT64,cache_miss:INT64,admitted:INT64
fi

echo "==> Cloud KMS key ring ${KEY_RING}"
if gcloud kms keyrings describe "${KEY_RING}" --location "${KMS_LOCATION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "    exists"
else
  gcloud kms keyrings create "${KEY_RING}" --location "${KMS_LOCATION}" --project "${PROJECT_ID}"
fi

echo "==> Cloud KMS signing key ${KEY_NAME}"
if gcloud kms keys describe "${KEY_NAME}" --keyring "${KEY_RING}" --location "${KMS_LOCATION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "    exists"
else
  gcloud kms keys create "${KEY_NAME}" \
    --keyring "${KEY_RING}" --location "${KMS_LOCATION}" --project "${PROJECT_ID}" \
    --purpose asymmetric-signing --default-algorithm rsa-sign-pss-2048-sha256 --protection-level software
fi

echo
echo "Done. Re-run the Agent Platform demo or UI: Dream-RSI now runs as SQL in BigQuery and hotpatches"
echo "are signed with Cloud KMS (RSA-PSS) and verified against the key's public key."
