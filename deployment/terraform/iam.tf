locals {
  project_ids = {
    prod    = var.prod_project_id
    staging = var.staging_project_id
  }
}

# Data source to get project numbers
data "google_project" "projects" {
  for_each   = local.project_ids
  project_id = each.value
}

# 1. Assign roles for the CICD project
resource "google_project_iam_member" "cicd_project_roles" {
  for_each = toset(var.cicd_roles)

  project    = var.cicd_runner_project_id
  role       = each.value
  member     = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]

}

# 2. Assign roles for the other two projects (prod and staging)
resource "google_project_iam_member" "other_projects_roles" {
  for_each = {
    for pair in setproduct(keys(local.project_ids), var.cicd_sa_deployment_required_roles) :
    "${pair[0]}-${pair[1]}" => {
      project_id = local.project_ids[pair[0]]
      role       = pair[1]
    }
  }

  project    = each.value.project_id
  role       = each.value.role
  member     = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}

# 3. Allow Cloud Run service SA to pull containers stored in the CICD project
resource "google_project_iam_member" "cicd_run_invoker_artifact_registry_reader" {
  for_each = local.project_ids
  project  = var.cicd_runner_project_id

  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:service-${data.google_project.projects[each.key].number}@serverless-robot-prod.iam.gserviceaccount.com"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]

}

# 4. Grant Cloud Run SA the required permissions to run the application
resource "google_project_iam_member" "cloud_run_app_sa_roles" {
  for_each = {
    for pair in setproduct(keys(local.project_ids), var.cloud_run_app_roles) :
    join(",", pair) => {
      project = local.project_ids[pair[0]]
      role    = pair[1]
    }
  }

  project    = each.value.project
  role       = each.value.role
  member     = "serviceAccount:${google_service_account.cloud_run_app_sa[split(",", each.key)[0]].email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}

# Special assignment: Allow the CICD SA to create tokens
resource "google_service_account_iam_member" "cicd_run_invoker_token_creator" {
  service_account_id = google_service_account.cicd_runner_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
# Special assignment: Allow the CICD SA to impersonate himself for trigger creation
resource "google_service_account_iam_member" "cicd_run_invoker_account_user" {
  service_account_id = google_service_account.cicd_runner_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
