resource "google_project_iam_member" "bigquery_data_editor" {
  for_each = local.project_ids

  project = each.value
  role    = "roles/bigquery.dataEditor"
  member  = module.log_export_to_bigquery[each.key].writer_identity
}

module "log_export_to_bigquery" {
  for_each = local.project_ids

  source  = "terraform-google-modules/log-export/google"
  version = "10.0.0"

  log_sink_name          = var.telemetry_sink_name
  parent_resource_type   = "project"
  parent_resource_id     = each.value
  destination_uri        = "bigquery.googleapis.com/projects/${each.value}/datasets/${var.telemetry_bigquery_dataset_id}"
  filter                 = var.telemetry_logs_filter
  bigquery_options       = { use_partitioned_tables = true }
  unique_writer_identity = true
  depends_on             = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]

}

resource "google_bigquery_dataset" "feedback_dataset" {
  for_each      = local.project_ids
  project       = each.value
  dataset_id    = var.feedback_bigquery_dataset_id
  friendly_name = var.feedback_bigquery_dataset_id
  location      = var.region
  depends_on    = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]

}

module "feedback_export_to_bigquery" {
  for_each = local.project_ids

  source                 = "terraform-google-modules/log-export/google"
  version                = "10.0.0"
  log_sink_name          = var.feedback_sink_name
  parent_resource_type   = "project"
  parent_resource_id     = each.value
  destination_uri        = "bigquery.googleapis.com/projects/${each.value}/datasets/${var.feedback_bigquery_dataset_id}"
  filter                 = var.feedback_logs_filter
  bigquery_options       = { use_partitioned_tables = true }
  unique_writer_identity = true
  depends_on             = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services, google_bigquery_dataset.feedback_dataset]
}

resource "google_bigquery_dataset" "telemetry_logs_dataset" {
  depends_on    = [module.log_export_to_bigquery, module.feedback_export_to_bigquery, resource.google_project_service.shared_services]
  for_each      = local.project_ids
  project       = each.value
  dataset_id    = var.telemetry_bigquery_dataset_id
  friendly_name = var.telemetry_bigquery_dataset_id
  location      = var.region
}