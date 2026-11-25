# Copyright 2026 Google LLC
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

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Asymmetric Cloud KMS signing key held exclusively by the Ingress Gateway for `ctx+jwt`.
resource "google_kms_key_ring" "cymbal_tenants" {
  name     = "cymbal-pooled-tenants"
  location = var.region
}

resource "google_kms_crypto_key" "context_token_signer" {
  name     = "cymbal-ctx-jwt-signer"
  key_ring = google_kms_key_ring.cymbal_tenants.id
  purpose  = "ASYMMETRIC_SIGN"

  version_template {
    algorithm        = "EC_SIGN_P256_SHA256"
    protection_level = "HSM"
  }
}

# Dedicated per-tenant Cloud KMS CMEK key + per-tenant Google Cloud Service Account.
resource "google_kms_crypto_key" "tenant_cmek" {
  for_each        = var.tenants
  name            = "cmek-${each.key}"
  key_ring        = google_kms_key_ring.cymbal_tenants.id
  purpose         = "ENCRYPT_DECRYPT"
  rotation_period = "7776000s"
}

resource "google_service_account" "tenant_workload" {
  for_each     = var.tenants
  account_id   = "ct-${substr(md5(each.key), 0, 12)}"
  display_name = "Pooled 2LO Service Account for ${each.key}"
}

resource "google_kms_crypto_key_iam_member" "tenant_cmek_user" {
  for_each      = var.tenants
  crypto_key_id = google_kms_crypto_key.tenant_cmek[each.key].id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${google_service_account.tenant_workload[each.key].email}"
}

# Stateless Cloud Run Turn Orchestrator (The Brain) with zero standing tenant credentials.
resource "google_service_account" "pooled_gateway" {
  account_id   = "cymbal-pooled-gateway"
  display_name = "Cymbal Pooled Ingress Gateway & Stateless Brain"
}

resource "google_kms_crypto_key_iam_member" "gateway_context_signer" {
  crypto_key_id = google_kms_crypto_key.context_token_signer.id
  role          = "roles/cloudkms.signerVerifier"
  member        = "serviceAccount:${google_service_account.pooled_gateway.email}"
}

resource "google_project_iam_member" "gateway_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.pooled_gateway.email}"
}

resource "google_cloud_run_v2_service" "pooled_gateway" {
  name     = "cymbal-pooled-gateway"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.pooled_gateway.email
    containers {
      image = var.gateway_image
      env {
        name  = "CYMBAL_LIVE_GEMINI"
        value = "1"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = "global"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "true"
      }
    }
  }
}
