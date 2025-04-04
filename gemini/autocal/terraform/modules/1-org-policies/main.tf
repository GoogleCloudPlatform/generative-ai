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

# Org policy configuration
#
# This should only be enabled if needed - e.g. you're using Argolis.
#
# It most likely will require you to run terraform as a service account which adds
# additional deployment complexity.
#
# set org_policies variable to true.

# Project Reference
data "google_project" "project" {
  project_id = var.project_id
}

# Enable Org Policy API
resource "google_project_service" "org_policy" {
  project            = data.google_project.project.id
  service            = "orgpolicy.googleapis.com"
  disable_on_destroy = false
}


# Allow services to be deployed without authentication
resource "google_org_policy_policy" "allowed_member_domains" {
  depends_on = [
    google_project_service.org_policy,
  ]

  name   = "projects/${data.google_project.project.project_id}/policies/iam.allowedPolicyMemberDomains"
  parent = "projects/${data.google_project.project.project_id}"

  spec {
    inherit_from_parent = false
    rules {
      allow_all = "TRUE"
    }
  }
}

