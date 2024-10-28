locals {
  services = [
    "aiplatform.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "bigquery.googleapis.com",
    "discoveryengine.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "bigquery.googleapis.com",
    "serviceusage.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com"
  ]
}

resource "google_project_service" "services" {
  count              = length(local.services)
  project            = var.dev_project_id
  service            = local.services[count.index]
  disable_on_destroy = false
}
