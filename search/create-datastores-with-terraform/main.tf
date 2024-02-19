/**
 * Copyright 2024 Google LLC
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

resource "random_id" "id" {
  byte_length = 4
}

resource "google_discovery_engine_data_store" "datastore-ds" {
  location                    = var.region
  data_store_id               = "${var.datastore_name}-ds-${random_id.id.hex}"
  display_name                = "${var.datastore_name}-ds"
  industry_vertical           = "GENERIC"
  content_config              = "CONTENT_REQUIRED"
  solution_types              = ["SOLUTION_TYPE_SEARCH"]
  create_advanced_site_search = true
  project                     = var.project_id
}

resource "google_discovery_engine_search_engine" "datastore-engine" {
  engine_id         = "${var.datastore_name}-engine-${random_id.id.hex}"
  collection_id     = "default_collection"
  location          = google_discovery_engine_data_store.datastore-ds.location
  display_name      = "${var.datastore_name}-engine"
  industry_vertical = "GENERIC"
  data_store_ids    = [google_discovery_engine_data_store.datastore-ds.data_store_id]
  common_config {
    company_name = var.company_name
  }
  search_engine_config {
    search_tier    = "SEARCH_TIER_ENTERPRISE"
    search_add_ons = ["SEARCH_ADD_ON_LLM"]
  }
  project = var.project_id
}
