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

output "image_bucket" {
  value       = google_storage_bucket.demo_images.name
  description = "Raw bucket name"
}

output "bigquery_editor_image_sp" {
  value       = "https://console.cloud.google.com/bigquery?project=${module.project-services.project_id}&ws=!1m5!1m4!6m3!1s${module.project-services.project_id}!2s${google_bigquery_dataset.demo_dataset.dataset_id}!3simage_query_remote_function_sp"
  description = "The URL to launch the BigQuery editor to invoke the image analysis procedure opened"
}

output "bigquery_editor_text_sp" {
  value       = "https://console.cloud.google.com/bigquery?project=${module.project-services.project_id}&ws=!1m5!1m4!6m3!1s${module.project-services.project_id}!2s${google_bigquery_dataset.demo_dataset.dataset_id}!3stext_query_remote_function_sp"
  description = "The URL to launch the BigQuery editor to invoke the image analysis procedure opened"
}
