terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "< 7.0.0"
    }
  }
}

locals {
  all_projects = [
    var.cicd_runner_project_id,
    var.prod_project_id,
    var.staging_project_id
  ]
}

resource "google_storage_bucket" "bucket_load_test_results" {
  name                        = "${var.cicd_runner_project_id}-${var.suffix_bucket_name_load_test_results}"
  location                    = var.region
  project                     = var.cicd_runner_project_id
  uniform_bucket_level_access = true
  force_destroy               = true
  depends_on                  = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}

resource "google_storage_bucket" "logs_data_bucket" {
  for_each                    = toset(local.all_projects)
  name                        = "${each.value}-logs-data"
  location                    = var.region
  project                     = each.value
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
