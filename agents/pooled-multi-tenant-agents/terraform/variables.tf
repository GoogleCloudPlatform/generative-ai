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

variable "project_id" {
  description = "Target Google Cloud project ID hosting the pooled multi-tenant tier."
  type        = string
}

variable "region" {
  description = "Primary Google Cloud region for Cloud Run, Cloud KMS, and Memory Bank."
  type        = string
  default     = "us-central1"
}

variable "gateway_image" {
  description = "Container image URI for the pooled Ingress Gateway and Brain runtime."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "gateway_ingress" {
  description = "Cloud Run ingress policy. Keep INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER for production ILB/IAP, or set INGRESS_TRAFFIC_ALL with IAM invoker auth for workstation verification."
  type        = string
  default     = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
}

variable "tenants" {
  description = "Configuration-driven tenant onboarding map (Pattern A: Governed Pool)."
  type = map(object({
    oidc_issuer     = string
    oidc_audience   = string
    entitled_agents = list(string)
  }))
  default = {
    "tenant-finvault-alpha" = {
      oidc_issuer   = "https://finvault.okta.com/oauth2/default"
      oidc_audience = "cymbal-cloudops-api"
      entitled_agents = [
        "cymbal_shared_diagnostic_agent",
        "finvault_regulatory_escalation_agent",
      ]
    }
    "tenant-retailstream-beta" = {
      oidc_issuer     = "https://login.microsoftonline.com/retailstream-tenant/v2.0"
      oidc_audience   = "cymbal-cloudops-api"
      entitled_agents = ["cymbal_shared_diagnostic_agent"]
    }
  }
}
