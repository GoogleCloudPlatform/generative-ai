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

output "gateway_uri" {
  description = "Cloud Run URI of the pooled Ingress Gateway & Stateless Brain."
  value       = google_cloud_run_v2_service.pooled_gateway.uri
}

output "context_signing_key_id" {
  description = "Cloud KMS asymmetric key resource ID for ctx+jwt signing."
  value       = google_kms_crypto_key.context_token_signer.id
}

output "tenant_service_accounts" {
  description = "Deterministic per-tenant 2LO service account emails."
  value       = { for k, sa in google_service_account.tenant_workload : k => sa.email }
}
