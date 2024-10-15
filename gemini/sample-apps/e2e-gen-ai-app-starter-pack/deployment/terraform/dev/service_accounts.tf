resource "google_service_account" "cloud_run_app_sa" {
  account_id   = var.cloud_run_app_sa_name
  display_name = "Cloud Run Generative AI app SA"
  project      = var.dev_project_id
  depends_on   = [resource.google_project_service.services]
}
