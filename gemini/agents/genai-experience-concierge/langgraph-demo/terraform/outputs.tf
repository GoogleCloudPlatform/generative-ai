# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

output "project-id" {
  value = module.project-factory.project_id
}

output "concierge-alloydb-connection-secret-name" {
  value = element(split("/", module.secret-manager.secret_names[0]), -1)
}

output "alloydb-cluster-id" {
  value = module.alloy-db.cluster_id
}

output "vpc-id" {
  value = module.vpc.network_id
}

output "subnet-id" {
  value = module.vpc.subnets_ids[0]
}

output "app-engine-host" {
  value = google_app_engine_application.app_engine.default_hostname
}

output "app-engine-service-account" {
  value = module.concierge_app_engine_service_account.email
}

output "cloud-run-service-account" {
  value = module.concierge_server_service_account.email
}

output "cloud-build-service-account" {
  value = module.concierge_build_service_account.email
}

output "artifact-registry-repo" {
  value = google_artifact_registry_repository.concierge-repo.name
}

output "artifact-registry-location" {
  value = google_artifact_registry_repository.concierge-repo.location
}

output "cymbal-retail-dataset-id" {
  value = google_bigquery_dataset.cymbal_retail_dataset.dataset_id
}

output "cymbal-retail-dataset-location" {
  value = google_bigquery_dataset.cymbal_retail_dataset.location
}

output "cymbal-retail-connection-id" {
  value = google_bigquery_connection.cymbal_connection.connection_id
}
