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

## Identity Platform
resource "google_identity_platform_config" "auth" {
  provider = google-beta
  project  = data.google_project.project.project_id
  lifecycle {
    ignore_changes = [
      authorized_domains,
      blocking_functions
    ]
  }
}

# Blocking function

# Build Source Bucket
resource "google_storage_bucket" "build" {
  name                        = "${data.google_project.project.project_id}-build-${random_string.id.result}"
  project                     = data.google_project.project.project_id
  location                    = var.bucket_location
  uniform_bucket_level_access = true
}

## Auth Blocking Function
locals {
  auth_block_root    = "${path.root}/../services/auth-blocking"
}

## Package up blocking function for deployment
data "archive_file" "auth_blocking" {
  type             = "zip"
  output_path      = "${path.module}/tmp/auth-blocking.zip"
  output_file_mode = "0666"

  source_dir = local.auth_block_root

  excludes = [
    ".env",
    "node_modules",
    "*.md",
    "lib",
  ]
}

resource "google_storage_bucket_object" "auth_blocking" {
  name   = "auth-blocking.zip"
  bucket = google_storage_bucket.build.name
  source = data.archive_file.auth_blocking.output_path
}

resource "google_cloudfunctions2_function" "before_signin" {
  name        = "auth-blocking-before-signin"
  location    = var.location
  description = "Auth blocking signin function"
  project     = data.google_project.project.project_id

  build_config {
    runtime     = "nodejs22"
    entry_point = "beforeSignIn"
    source {
      storage_source {
        bucket = google_storage_bucket.build.name
        object = google_storage_bucket_object.auth_blocking.name
      }
    }
    service_account = "projects/${data.google_project.project.project_id}/serviceAccounts/${google_service_account.auth_blocking_build.email}"
  }

  service_config {
    available_memory = "256M"
    available_cpu    = "1"
    service_account_email = google_service_account.auth_blocking_function.email
  }
}

# Allow public access (required for auth blocking functions)
resource "google_cloud_run_service_iam_member" "before_signin" {
  project  = data.google_project.project.project_id
  location = google_cloudfunctions2_function.before_signin.location
  service  = google_cloudfunctions2_function.before_signin.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloudfunctions2_function" "before_create" {
  name        = "auth-blocking-before-create"
  location    = var.location
  description = "Auth blocking before create function"
  project     = data.google_project.project.project_id

  build_config {
    runtime     = "nodejs22"
    entry_point = "beforeCreate"
    source {
      storage_source {
        bucket = google_storage_bucket.build.name
        object = google_storage_bucket_object.auth_blocking.name
      }
    }
    service_account = "projects/${data.google_project.project.project_id}/serviceAccounts/${google_service_account.auth_blocking_build.email}"
  }

  service_config {
    available_memory = "256M"
    available_cpu    = "1"
    service_account_email = google_service_account.auth_blocking_function.email
  }
}

# Allow public access (required for auth blocking functions)
resource "google_cloud_run_service_iam_member" "before_create" {
  project  = data.google_project.project.project_id
  location = google_cloudfunctions2_function.before_create.location
  service  = google_cloudfunctions2_function.before_create.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
