# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

locals {
  concierge_server_service_account_name     = "concierge-server"
  concierge_build_service_account_name      = "concierge-build"
  concierge_app_engine_service_account_name = "concierge-app-engine"
}

# Create a project for the concierge demo.
module "project-factory" {
  source  = "terraform-google-modules/project-factory/google"
  version = "~> 18.0"

  name              = var.project_name
  project_id        = var.project_id
  org_id            = var.org_id
  folder_id         = var.folder_id
  billing_account   = var.billing_account
  random_project_id = var.random_project_suffix

  deletion_policy = "DELETE"

  default_service_account = "disable"

  activate_apis = [
    "compute.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "vpcaccess.googleapis.com",
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "iam.googleapis.com",
    "alloydb.googleapis.com",
    "appengine.googleapis.com",
    "appengineflex.googleapis.com",
    "iap.googleapis.com",
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
  ]
}

# Create an Artifact Registry repository for hosting docker images for the concierge demo.
resource "google_artifact_registry_repository" "concierge-repo" {
  project       = module.project-factory.project_id
  location      = var.region
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"

  depends_on = [module.project-factory]
}
