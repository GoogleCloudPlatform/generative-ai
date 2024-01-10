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

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.52, < 6"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 2"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.9.1"
    }
    http = {
      source  = "hashicorp/http"
      version = ">= 3.4.1"
    }
  }
  required_version = ">= 0.13"

  provider_meta "google" {
    module_name = "blueprints/terraform/terraform-google-bigquery:data_warehouse/v7.0.0"
  }
}
