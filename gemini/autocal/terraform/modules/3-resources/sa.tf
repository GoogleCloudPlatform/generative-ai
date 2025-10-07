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

## Service Accounts

# Cloud Build & Deploy SA
resource "google_service_account" "build_and_deploy" {
  account_id   = "build-and-deploy"
  display_name = "Build and Deploy SA"
  project      = data.google_project.project.project_id
}
# Grant permissions on build project
resource "google_project_iam_member" "build_and_deploy" {
  for_each = toset(local.build_and_deploy_sa_roles)
  project  = data.google_project.project.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.build_and_deploy.email}"
  lifecycle {
    ignore_changes = [
      id,
      member
    ]
  }
}

# AutoCal App SA
resource "google_service_account" "autocal" {
  account_id   = "autocal-app"
  display_name = "AutoCal App"
  project      = data.google_project.project.project_id
}

# Grant permissions to AutoCal App SA
resource "google_project_iam_member" "autocal" {
  for_each = toset(concat(local.cloud_run_iam_roles, local.autocal_sa_roles))
  project  = data.google_project.project.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.autocal.email}"
  lifecycle {
    ignore_changes = [
      id,
      member
    ]
  }
}


# AutoCal Backend Service SA
resource "google_service_account" "autocal_service" {
  account_id   = "autocal-service"
  display_name = "AutoCal Service"
  project      = data.google_project.project.project_id
}

# Grant permissions to AutoCal Backend SA
resource "google_project_iam_member" "autocal_service" {
  for_each = toset(concat(local.cloud_run_iam_roles, local.autocal_service_sa_roles))
  project  = data.google_project.project.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.autocal_service.email}"
  lifecycle {
    ignore_changes = [
      id,
      member
    ]
  }
}

# Auth blocking Function SA
resource "google_service_account" "auth_blocking_function" {
  account_id   = "auth-blocking-function"
  display_name = "Auth blocking Function"
  project      = data.google_project.project.project_id
}

# Grant permissions to Auth blocking Function SA
resource "google_project_iam_member" "auth_blocking_function" {
  for_each = toset(concat(local.cloud_run_iam_roles, local.auth_blocking_function_sa_roles))
  project  = data.google_project.project.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.auth_blocking_function.email}"
  lifecycle {
    ignore_changes = [
      id,
      member
    ]
  }
}

# Auth Blocking Build SA
resource "google_service_account" "auth_blocking_build" {
  account_id   = "auth-blocking-build"
  display_name = "Auth Blocking Build"
  project      = data.google_project.project.project_id
}

# Grant permissions to Auth Blocking Build SA
resource "google_project_iam_member" "auth_blocking_build" {
  for_each = toset(local.auth_blocking_build_sa_roles)
  project  = data.google_project.project.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.auth_blocking_build.email}"
  lifecycle {
    ignore_changes = [
      id,
      member
    ]
  }
}

# Image processor Function SA
resource "google_service_account" "image_processor_image_processorfunction" {
  account_id   = "image-processor-function"
  display_name = "Image processor Function"
  project      = data.google_project.project.project_id
}

# Grant permissions to Image processor Function SA
resource "google_project_iam_member" "image_processor_image_processorfunction" {
  for_each = toset(concat(local.cloud_run_iam_roles, local.autocal_service_sa_roles))
  project  = data.google_project.project.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.image_processor_image_processorfunction.email}"
  lifecycle {
    ignore_changes = [
      id,
      member
    ]
  }
}

# Image processor Build SA
resource "google_service_account" "image_processor_image_processor_build" {
  account_id   = "image-processor-build"
  display_name = "Image processor Build"
  project      = data.google_project.project.project_id
}

# Grant permissions to Image processor Build SA
resource "google_project_iam_member" "image_processor_image_processor_build" {
  for_each = toset(local.image_processor_image_processor_build_sa_roles)
  project  = data.google_project.project.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.image_processor_image_processor_build.email}"
  lifecycle {
    ignore_changes = [
      id,
      member
    ]
  }
}

# Image Processor Trigger SA
resource "google_service_account" "image_processor_trigger" {
  account_id   = "image-processor-trigger"
  display_name = "Image Processor Trigger"
  project      = data.google_project.project.project_id
}

# Grant permissions to Image Processor SA
resource "google_project_iam_member" "image_processor_trigger" {
  for_each = toset(local.image_processor_trigger_sa_roles)
  project  = data.google_project.project.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.image_processor_trigger.email}"
  lifecycle {
    ignore_changes = [
      id,
      member
    ]
  }
}
