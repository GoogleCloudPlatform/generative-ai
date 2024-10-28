# a. Create PR checks trigger
resource "google_cloudbuild_trigger" "pr_checks" {
  name            = "pr-checks"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"
    pull_request {
      branch = "main"
    }
  }

  filename = "deployment/ci/pr_checks.yaml"
  included_files = [
    "app/**",
    "tests/**",
    "deployment/**",
    "poetry.lock"
  ]
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}

# b. Create CD pipeline trigger
resource "google_cloudbuild_trigger" "cd_pipeline" {
  name            = "cd-pipeline"
  project         = var.cicd_runner_project_id
  location        = var.region
  service_account = resource.google_service_account.cicd_runner_sa.id
  description     = "Trigger for CD pipeline"

  repository_event_config {
    repository = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"
    push {
      branch = "main"
    }
  }

  filename = "deployment/cd/staging.yaml"
  included_files = [
    "app/**",
    "tests/**",
    "deployment/**",
    "poetry.lock"
  ]
  substitutions = {
    _STAGING_PROJECT_ID            = var.staging_project_id
    _PROD_PROJECT_ID               = var.prod_project_id
    _BUCKET_NAME_LOAD_TEST_RESULTS = resource.google_storage_bucket.bucket_load_test_results.name
    _ARTIFACT_REGISTRY_REPO_NAME   = var.artifact_registry_repo_name
    _CLOUD_RUN_APP_SA_NAME         = var.cloud_run_app_sa_name
    _REGION                        = var.region
  }
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]

}

# c. Create Deploy to production trigger
resource "google_cloudbuild_trigger" "deploy_to_prod_pipeline" {
  name            = "deploy-to-prod-pipeline"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for deployment to production"
  service_account = resource.google_service_account.cicd_runner_sa.id
  repository_event_config {
    repository = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"
  }
  filename = "deployment/cd/deploy-to-prod.yaml"
  approval_config {
    approval_required = true
  }
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]

}
