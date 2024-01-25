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

module "project-services" {
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "14.4"
  disable_services_on_destroy = false

  project_id  = var.project_id
  enable_apis = var.enable_apis

  activate_apis = [
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
    "bigquerystorage.googleapis.com",
    "cloudapis.googleapis.com",
    "cloudfunctions.googleapis.com",
    "config.googleapis.com",
    "dataflow.googleapis.com",
    "dataform.googleapis.com",
    "logging.googleapis.com",
    "notebooks.googleapis.com",
    "run.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "storage-api.googleapis.com",
    "workflows.googleapis.com",
    "visionai.googleapis.com",
  ]

  activate_api_identities = [
    {
      api = "workflows.googleapis.com"
      roles = [
        "roles/workflows.viewer"
      ]
      api = "cloudfunctions.googleapis.com"
      roles = [
        "roles/cloudfunctions.invoker"
      ]
      api = "run.googleapis.com"
      roles = [
        "roles/run.invoker"
      ]
    }
  ]
}

# Create random ID to be used for deployment uniqueness
resource "random_id" "id" {
  byte_length = 4
}

# Define/create zip file as a source for the image analysis Cloud Function
data "archive_file" "create_image_function_zip" {
  type        = "zip"
  output_path = "${path.root}/tmp/image_function_source.zip"
  source_dir  = "${path.root}/function/image/"
}

# Define/create zip file as a source for the image analysis Cloud Function
data "archive_file" "create_text_function_zip" {
  type        = "zip"
  output_path = "${path.root}/tmp/text_function_source.zip"
  source_dir  = "${path.root}/function/text/"
}

# Wait until after the APIs are activated to being setting up infrastructure
resource "time_sleep" "wait_after_apis" {
  create_duration = "90s"
  depends_on      = [module.project-services]
}

data "google_client_config" "current" {
  depends_on = [time_sleep.wait_after_apis]
}

# Wait until the Cloud Workflow has finished to complete setup
resource "time_sleep" "wait_after_workflow" {
  create_duration = "30s"
  depends_on = [
    data.http.call_workflows_setup
  ]
}
