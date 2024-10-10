resource "google_service_account" "cicd_runner_sa" {
  account_id   = var.cicd_runner_sa_name
  display_name = "CICD Runner SA"
  project      = var.cicd_runner_project_id
  depends_on   = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}

resource "google_service_account" "cloud_run_app_sa" {
  for_each = local.project_ids

  account_id   = var.cloud_run_app_sa_name
  display_name = "Cloud Run Generative AI app SA"
  project      = each.value
  depends_on   = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
