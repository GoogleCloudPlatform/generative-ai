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

# Blog Section 1: Issuer-Bound Workload Identity Federation (WIF) per Tenant
resource "google_iam_workload_identity_pool" "cymbal_tenants" {
  workload_identity_pool_id = "cymbal-pooled-tenants"
  display_name              = "Cymbal Pooled Tenant Pool"
}

resource "google_iam_workload_identity_pool_provider" "tenant_oidc" {
  for_each                           = var.tenants
  workload_identity_pool_id          = google_iam_workload_identity_pool.cymbal_tenants.workload_identity_pool_id
  workload_identity_pool_provider_id = "idp-${substr(md5(each.key), 0, 10)}"
  display_name                       = substr("OIDC ${each.key}", 0, 32)

  attribute_mapping = {
    "google.subject"      = "assertion.sub"
    "attribute.tenant_id" = "'${each.key}'"
    "attribute.user_role" = "assertion.groups"
  }

  attribute_condition = "assertion.iss == '${each.value.oidc_issuer}'"

  oidc {
    issuer_uri        = each.value.oidc_issuer
    allowed_audiences = [each.value.oidc_audience]
  }
}

# Blog Section 3 (Control 2): Cloud IAM memoryScope CEL Condition on Memory Bank in Gemini
locals {
  tenant_agent_pairs = merge([
    for tenant_id, cfg in var.tenants : {
      for agent_id in cfg.entitled_agents :
      "${tenant_id}:${agent_id}" => {
        tenant_id = tenant_id
        agent_id  = agent_id
      }
    }
  ]...)
}

resource "google_project_iam_member" "memory_bank_cel_scope" {
  for_each = local.tenant_agent_pairs
  project  = var.project_id
  role     = "roles/aiplatform.memoryUser"
  member   = "serviceAccount:${google_service_account.tenant_workload[each.value.tenant_id].email}"

  condition {
    title       = "memory-scope-${each.value.tenant_id}-${each.value.agent_id}"
    description = "Locks tenant 2LO SA strictly to its own tenant_id and agent_id in Memory Bank."
    expression  = "api.getAttribute('aiplatform.googleapis.com/memoryScope', {})['tenant_id'] == '${each.value.tenant_id}' && api.getAttribute('aiplatform.googleapis.com/memoryScope', {})['agent_id'] == '${each.value.agent_id}'"
  }
}
