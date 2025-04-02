# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# Dynamic GCS backend configuration.
terraform {
  required_version = "~> 1.11"

  backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.25"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }
}
