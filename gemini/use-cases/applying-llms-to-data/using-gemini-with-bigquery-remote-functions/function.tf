/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


#Create a service account to manage the remote function and its permissions
resource "google_service_account" "cloud_function_manage_sa" {
  project      = module.project-services.project_id
  account_id   = "gemini-demo"
  display_name = "Cloud Functions Service Account"

  depends_on = [
    time_sleep.wait_after_apis,
  ]
}

locals {
  cloud_function_roles = [
    "roles/cloudfunctions.admin",    // Service account role to manage access to the remote function
    "roles/run.invoker",             // Service account role to invoke the remote function
    "roles/storage.objectAdmin",     // Read/write GCS files
    "roles/bigquery.admin",          // Create jobs and modify BigQuery tables
    "roles/aiplatform.user",         // Needs to predict from endpoints
    "roles/aiplatform.serviceAgent", // Service account role
    "roles/iam.serviceAccountUser"
  ]
}

resource "google_project_iam_member" "function_manage_roles" {
  count   = length(local.cloud_function_roles)
  project = module.project-services.project_id
  role    = local.cloud_function_roles[count.index]
  member  = "serviceAccount:${google_service_account.cloud_function_manage_sa.email}"

  depends_on = [google_service_account.cloud_function_manage_sa]
}

## Create a Cloud Function to serve as the remote function for image analysis
resource "google_cloudfunctions2_function" "image_remote_function" {
  name        = "gemini-bq-demo-image"
  project     = module.project-services.project_id
  location    = var.region
  description = "A Cloud Function that uses the Gemini Generative Model to analyze and describe images."

  build_config {
    runtime     = "python311"
    entry_point = "run_it"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.image_source_upload.name
      }
    }
  }

  service_config {
    max_instance_count = 10
    # min_instance_count can be set to 1 to improve performance and responsiveness
    min_instance_count               = 0
    available_memory                 = "512Mi"
    timeout_seconds                  = 300
    max_instance_request_concurrency = 5
    available_cpu                    = "2"
    ingress_settings                 = "ALLOW_ALL"
    all_traffic_on_latest_revision   = true
    service_account_email            = google_service_account.cloud_function_manage_sa.email
    environment_variables = {
      "PROJECT_ID" : module.project-services.project_id,
    "REGION" : var.region }
  }
  depends_on = [time_sleep.wait_after_apis]
}

## Create a Cloud Function to serve as the remote function for image analysis
resource "google_cloudfunctions2_function" "text_remote_function" {
  name        = "gemini-bq-demo-text"
  project     = module.project-services.project_id
  location    = var.region
  description = "A Cloud Function that uses the Gemini Generative Model to analyze and generate text."

  build_config {
    runtime     = "python311"
    entry_point = "run_it"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.text_source_upload.name
      }
    }
  }

  service_config {
    max_instance_count = 10
    # min_instance_count can be set to 1 to improve performance and responsiveness
    min_instance_count               = 0
    available_memory                 = "512Mi"
    timeout_seconds                  = 300
    max_instance_request_concurrency = 5
    available_cpu                    = "2"
    ingress_settings                 = "ALLOW_ALL"
    all_traffic_on_latest_revision   = true
    service_account_email            = google_service_account.cloud_function_manage_sa.email
    environment_variables = {
      "PROJECT_ID" : module.project-services.project_id,
    "REGION" : var.region }
  }
  depends_on = [time_sleep.wait_after_apis]
}

# Wait until after the function is created to deconflict resource creation
resource "time_sleep" "wait_after_functions" {
  create_duration = "10s"
  depends_on = [
    google_cloudfunctions2_function.image_remote_function,
    google_cloudfunctions2_function.text_remote_function,
  ]
}
