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
  # All APIs to deploy
  apis = [
    "orgpolicy.googleapis.com",
    "run.googleapis.com",
    "firebasestorage.googleapis.com",
    "identitytoolkit.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "firebaseextensions.googleapis.com",
    "eventarc.googleapis.com",
    "pubsub.googleapis.com",
    "aiplatform.googleapis.com",
    "discoveryengine.googleapis.com",
    "firestore.googleapis.com",
    "firebaserules.googleapis.com",
    "secretmanager.googleapis.com",
    "calendar-json.googleapis.com",
  ]
}
