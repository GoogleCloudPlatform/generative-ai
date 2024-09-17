locals {
  project_ids = {
    dev = var.dev_project_id
  }
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

  project = each.value.project
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.cloud_run_app_sa.email}"
}
