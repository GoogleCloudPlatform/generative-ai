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


# Set up the Workflow
## Create the Workflows service account to manage permissions
resource "google_service_account" "workflow_service_account" {
  project      = module.project-services.project_id
  account_id   = "cloud-workflow-sa-${random_id.id.hex}"
  display_name = "Service Account for Cloud Workflows"
  depends_on   = [time_sleep.wait_after_apis]
}

locals {
  workflow_roles = [
    "roles/workflows.admin",
    "roles/run.invoker",
    "roles/cloudfunctions.invoker",
    "roles/iam.serviceAccountTokenCreator",
    "roles/storage.objectAdmin",
    "roles/bigquery.connectionAdmin",
    "roles/bigquery.jobUser",
    "roles/bigquery.dataEditor",
  ]
}

## Grant the Workflow service account access needed to execute its tasks
resource "google_project_iam_member" "workflow_service_account_roles" {
  count      = length(local.workflow_roles)
  project    = module.project-services.project_id
  role       = local.workflow_roles[count.index]
  member     = "serviceAccount:${google_service_account.workflow_service_account.email}"
  depends_on = [google_project_iam_member.functions_invoke_roles]
}

## Create the workflow
resource "google_workflows_workflow" "workflow" {
  name            = "initial-workflow"
  project         = module.project-services.project_id
  region          = var.region
  description     = "Runs post Terraform setup steps for Solution in Console"
  service_account = google_service_account.workflow_service_account.id

  source_contents = templatefile("${path.module}/templates/workflow.tftpl", {
    sample_bucket = google_storage_bucket.demo_images.name,
    dataset_id    = google_bigquery_dataset.demo_dataset.dataset_id
  })

  depends_on = [
    google_service_account.workflow_service_account,
    google_bigquery_connection.function_connection,
    google_bigquery_routine.image_create_remote_function_sp,
    google_bigquery_routine.image_query_remote_function_sp,
    google_bigquery_routine.provision_text_sample_table_sp,
    google_bigquery_routine.text_create_remote_function_sp,
    google_bigquery_routine.text_query_remote_function_sp,
    google_bigquery_table.object_table,
    google_cloudfunctions2_function.image_remote_function,
    google_cloudfunctions2_function.text_remote_function,
    google_storage_bucket.demo_images,
    google_project_iam_member.functions_invoke_roles,
    time_sleep.wait_after_functions,
  ]
}

## Trigger the execution of the setup workflow
data "http" "call_workflows_setup" {
  url    = "https://workflowexecutions.googleapis.com/v1/projects/${module.project-services.project_id}/locations/${var.region}/workflows/${google_workflows_workflow.workflow.name}/executions"
  method = "POST"
  request_headers = {
    Accept = "application/json"
  Authorization = "Bearer ${data.google_client_config.current.access_token}" }
  depends_on = [
    google_workflows_workflow.workflow,
    google_bigquery_connection.function_connection,
    google_bigquery_routine.image_create_remote_function_sp,
    google_bigquery_routine.image_query_remote_function_sp,
    google_bigquery_routine.provision_text_sample_table_sp,
    google_bigquery_routine.text_create_remote_function_sp,
    google_bigquery_routine.text_query_remote_function_sp,
    google_bigquery_table.object_table,
    google_cloudfunctions2_function.image_remote_function,
    google_cloudfunctions2_function.text_remote_function,
    google_storage_bucket.demo_images,
    google_project_iam_member.functions_invoke_roles,
    time_sleep.wait_after_functions,
  ]
}
