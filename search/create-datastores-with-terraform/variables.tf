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

variable "project_id" {
  description = "Project ID"
  type        = string
}

variable "region" {
  description = "Region where the resources will be created"
  type        = string
  default     = "us-central1"
}

variable "company_name" {
  description = "Name of company for which datastore is being created"
  type        = string
}

variable "datastore_name" {
  description = "Name of the datasore"
  type        = string
}

variable "outputs_location" {
  description = "Locaton of tfvars file where outputs will be stored"
  type        = string
  default     = null
}
