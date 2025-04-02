# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# REQUIRED

variable "seed_project_id" {
  type = string
}

variable "project_id" {
  type = string
}

variable "billing_account" {
  type = string
}

variable "iap_support_email" {
  type = string
}

variable "app_engine_users" {
  type = list(string)
}

# OPTIONAL

variable "org_id" {
  type    = string
  default = null
}

variable "folder_id" {
  type    = string
  default = null
}

variable "project_name" {
  type    = string
  default = "Gen AI Concierge Demo"
}

variable "application_title" {
  type    = string
  default = "Gen AI Experience Concierge Demo"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

variable "app_engine_location" {
  type    = string
  default = "us-central"
}

variable "artifact_registry_repo" {
  type    = string
  default = "concierge"
}

variable "bigquery_dataset_location" {
  type    = string
  default = "US"
}

variable "random_project_suffix" {
  type    = bool
  default = false
}
