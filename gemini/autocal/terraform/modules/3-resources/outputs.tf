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

output "firebase_config" {
  description = "Firebase Config"
  value = {
    appId             = google_firebase_web_app.autocal.app_id
    apiKey            = data.google_firebase_web_app_config.autocal.api_key
    authDomain        = data.google_firebase_web_app_config.autocal.auth_domain
    databaseURL       = lookup(data.google_firebase_web_app_config.autocal, "database_url", "")
    storageBucket     = google_storage_bucket.firebase.name
    messagingSenderId = lookup(data.google_firebase_web_app_config.autocal, "messaging_sender_id", "")
    measurementId     = lookup(data.google_firebase_web_app_config.autocal, "measurement_id", "")
  }
}
