# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# Configure defaults using the seed project.
provider "google" {
  project               = var.seed_project_id
  region                = var.region
  zone                  = var.zone
  billing_project       = var.seed_project_id
  user_project_override = true
}
