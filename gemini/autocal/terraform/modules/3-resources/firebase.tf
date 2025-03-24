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

# Enable Firebase on project
resource "google_firebase_project" "firebase" {
  provider = google-beta
  project  = data.google_project.project.project_id
}


# Create Firebase storage bucket
resource "google_storage_bucket" "firebase" {
  provider                    = google-beta
  name                        = "${data.google_project.project.project_id}-assets-${random_string.id.result}"
  project                     = data.google_project.project.project_id
  location                    = var.bucket_location
  uniform_bucket_level_access = true
  lifecycle {
    ignore_changes = [
      cors
    ]
  }
}

resource "google_firebase_storage_bucket" "firebase" {
  provider  = google-beta
  project   = data.google_project.project.project_id
  bucket_id = google_storage_bucket.firebase.id
}

# Configure Firebase storage security rules
resource "google_firebaserules_ruleset" "storage" {
  provider = google-beta
  project  = data.google_project.project.project_id
  source {
    files {
      name    = "storage.rules"
      content = file("${path.module}/resources/storage.rules")
    }
  }
  depends_on = [
    google_firebase_storage_bucket.firebase
  ]
}
resource "google_firebaserules_release" "storage_primary" {
  provider     = google-beta
  name         = "firebase.storage/${google_storage_bucket.firebase.name}"
  ruleset_name = "projects/${data.google_project.project.project_id}/rulesets/${google_firebaserules_ruleset.storage.name}"
  project      = data.google_project.project.project_id

  lifecycle {
    replace_triggered_by = [
      google_firebaserules_ruleset.storage
    ]
  }

  depends_on = [
    google_storage_bucket.firebase,
  ]
}

### Provision a default Firestore database instance.
resource "google_firestore_database" "default" {
  project     = data.google_project.project.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"
}

# Configure Firestore security rules
resource "google_firebaserules_ruleset" "firestore" {
  depends_on = [
    google_firestore_database.default,
  ]
  source {
    files {
      name    = "firestore.rules"
      content = file("${path.module}/resources/firestore.rules")
    }
  }
  project = data.google_project.project.project_id
}

resource "google_firebaserules_release" "firestore_primary" {
  name         = "cloud.firestore"
  ruleset_name = "projects/${data.google_project.project.project_id}/rulesets/${google_firebaserules_ruleset.firestore.name}"
  project      = data.google_project.project.project_id

  lifecycle {
    replace_triggered_by = [
      google_firebaserules_ruleset.firestore
    ]
  }
  depends_on = [
    google_firestore_database.default,
  ]
}

# Create web apps for our use-cases
resource "google_firebase_web_app" "autocal" {
  provider     = google-beta
  project      = data.google_project.project.project_id
  display_name = "AutoCal"

  # The other App types (Android and Apple) use "DELETE" by default.
  # Web apps don't use "DELETE" by default due to backward-compatibility.
  deletion_policy = "DELETE"

  # Wait for Firebase to be enabled in the Google Cloud project before creating this App.
  depends_on = [
    google_firebase_project.firebase,
  ]
}
data "google_firebase_web_app_config" "autocal" {
  provider = google-beta
  project  = data.google_project.project.project_id

  web_app_id = google_firebase_web_app.autocal.app_id
}
