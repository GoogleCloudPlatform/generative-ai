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

## Deploy everything needed to build this app.
# Split into three modules to allow simpler breaks between org policies, API enablement, and resources.

# Deploy org policies first
module "org_policies" {
  count      = var.org_policies ? 1 : 0
  source     = "./modules/1-org-policies"
  project_id = var.project_id
}

module "host_apis" {
  source     = "./modules/2-apis"
  project_id = var.project_id
  apis       = local.apis
}

module "resources" {
  depends_on         = [module.host_apis, module.org_policies, time_sleep.delay_after_apis, time_sleep.delay_after_org_policies]
  source             = "./modules/3-resources"
  project_id         = var.project_id
  location           = var.location
  firestore_location = var.firestore_location
  bucket_location    = var.bucket_location
}

# Hacks to work around org policy and api propogation
resource "time_sleep" "delay_after_org_policies" {
  depends_on      = [module.org_policies]
  create_duration = "30s"
}
resource "time_sleep" "delay_after_apis" {
  depends_on      = [module.host_apis]
  create_duration = "30s"
}

