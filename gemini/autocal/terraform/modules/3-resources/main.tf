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

# Get project data field
data "google_project" "project" {
  project_id = var.project_id
}

# Create a random ID to use for resources
resource "random_string" "id" {
  length  = 4
  upper   = false
  special = false
}

## Artifact Registry
resource "google_artifact_registry_repository" "repo" {
  location      = var.location
  repository_id = "images"
  description   = "Image Repository"
  format        = "DOCKER"
  project       = data.google_project.project.project_id
}

# Artifact registry IAM permissions
data "google_iam_policy" "repo" {
  # These can write to the registry (typically builders)
  binding {
    role = "roles/artifactregistry.writer"
    members = [
      "serviceAccount:${google_service_account.build_and_deploy.email}",
    ]
  }
}

# Link the policies to the artifact registry
resource "google_artifact_registry_repository_iam_policy" "repo" {
  project     = google_artifact_registry_repository.repo.project
  location    = google_artifact_registry_repository.repo.location
  repository  = google_artifact_registry_repository.repo.name
  policy_data = data.google_iam_policy.repo.policy_data
  lifecycle {
    ignore_changes = [
      policy_data,
    ]
  }
}
