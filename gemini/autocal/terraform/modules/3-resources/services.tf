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

# # AutoCal App Empty Service
# resource "google_cloud_run_v2_service" "autocal_app" {
#   name                = "autocal-app"
#   location            = var.location
#   deletion_protection = false
#   ingress             = "INGRESS_TRAFFIC_ALL"
#   project             = data.google_project.project.project_id

#   template {
#     service_account = google_service_account.autocal.email
#     containers {
#       image = "us-docker.pkg.dev/cloudrun/container/hello"
#       env {
#         name  = "NEXT_PUBLIC_FIREBASE_API_KEY"
#         value = data.google_firebase_web_app_config.autocal.api_key
#       }
#       env {
#         name  = "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN"
#         value = data.google_firebase_web_app_config.autocal.auth_domain
#       }
#       env {
#         name  = "NEXT_PUBLIC_FIREBASE_PROJECT_ID"
#         value = data.google_project.project.project_id
#       }
#       env {
#         name  = "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET"
#         value = google_storage_bucket.firebase.name
#       }
#       env {
#         name  = "NEXT_PUBLIC_FIREBASE_MESSAGE_SENDER_ID"
#         value = lookup(data.google_firebase_web_app_config.autocal, "messaging_sender_id", "")
#       }
#       env {
#         name  = "NEXT_PUBLIC_FIREBASE_APP_ID"
#         value = google_firebase_web_app.autocal.app_id
#       }
#       env {
#         name  = "NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID"
#         value = lookup(data.google_firebase_web_app_config.autocal, "measurement_id", "")
#       }
#       env {
#         name  = "NEXT_PUBLIC_LOCATION"
#         value = var.location
#       }
#       resources {
#         limits = {
#           cpu    = "1"
#           memory = "512Mi"
#         }
#         startup_cpu_boost = true
#       }
#     }
#   }
#   lifecycle {
#     ignore_changes = [
#       client,
#       client_version,
#       template[0].containers[0].image,
#     ]
#   }
# }

# # Allow public access (auth handled in app code)
# resource "google_cloud_run_service_iam_member" "autocal_app" {
#   project  = data.google_project.project.project_id
#   location = google_cloud_run_v2_service.autocal_app.location
#   service  = google_cloud_run_v2_service.autocal_app.name
#   role     = "roles/run.invoker"
#   member   = "allUsers"
# }
