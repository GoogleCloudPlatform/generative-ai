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

locals {
  build_and_deploy_sa_roles = [
    "roles/storage.objectViewer",
    "roles/artifactregistry.writer",
    "roles/run.developer",
    "roles/iam.serviceAccountUser",
    "roles/cloudfunctions.admin",
    "roles/logging.logWriter",
  ]

  # For all Cloud Run services
  cloud_run_iam_roles = [
    "roles/cloudtrace.agent",
  ]

  # AutoCal App SA
  autocal_sa_roles = [
    "roles/datastore.user",
    "roles/logging.logWriter"
  ]

  # AutoCal Backend Service
  autocal_service_sa_roles = [
    "roles/datastore.user",
    // Allow access to Vertex AI
    "roles/aiplatform.user",
    "roles/storage.objectViewer"
  ]

  # Auth blocking Service Accounts
  auth_blocking_function_sa_roles = [
    "roles/datastore.user",
  ]
  auth_blocking_build_sa_roles = [
    "roles/artifactregistry.writer",
    "roles/run.developer",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/cloudfunctions.admin",
    "roles/storage.objectViewer"
  ]

  image_processor_image_processor_build_sa_roles = [
    "roles/artifactregistry.writer",
    "roles/run.developer",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/cloudfunctions.admin",
    "roles/storage.objectViewer"
  ]

  image_processor_trigger_sa_roles = [
    "roles/eventarc.eventReceiver"
  ]


}


