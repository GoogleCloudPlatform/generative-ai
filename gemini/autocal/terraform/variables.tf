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

variable "project_id" {
  type        = string
  description = "Host Project ID"
}

variable "org_policies" {
  type        = bool
  description = "Whether to enable org policies or not"
}

variable "location" {
  type        = string
  description = "Location (region) to deploy to"
}

variable "firestore_location" {
  type        = string
  description = "Location (region) to deploy firestore (e.g. eur3)"
}

variable "bucket_location" {
  type        = string
  description = "Location (region) to deploy bucket (e.g. eu)"
}
