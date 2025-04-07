# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# Create a demo IAP brand for the Oauth Consent Screen.
resource "google_iap_brand" "project_brand" {
  support_email     = var.iap_support_email
  application_title = var.application_title
  project           = module.project-factory.project_id

  depends_on = [module.project-factory]
}

# Create a demo IAP client for the Oauth Consent Screen.
resource "google_iap_client" "project_client" {
  display_name = "${var.application_title} Client"
  brand        = google_iap_brand.project_brand.name

  depends_on = [module.project-factory]
}

# Initialize the App Engine Application with IAP configured.
resource "google_app_engine_application" "app_engine" {
  project     = module.project-factory.project_id
  location_id = var.app_engine_location

  iap {
    enabled              = true
    oauth2_client_id     = google_iap_client.project_client.client_id
    oauth2_client_secret = google_iap_client.project_client.secret
  }

  depends_on = [module.project-factory]
}

# Policy for allow-listing the demo users.
data "google_iam_policy" "app_engine_access_policy" {
  binding {
    role    = "roles/iap.httpsResourceAccessor"
    members = var.app_engine_users
  }
}

# Apply the demo user policy to the App Engine Application.
resource "google_iap_web_type_app_engine_iam_policy" "app_engine_iap_policy" {
  project = google_app_engine_application.app_engine.project
  app_id  = google_app_engine_application.app_engine.app_id

  policy_data = data.google_iam_policy.app_engine_access_policy.policy_data

  depends_on = [module.project-factory]
}

# Configure IAP settings for the App Engine Application.
resource "google_iap_settings" "app_engine_iap_settings" {
  name = "projects/${google_app_engine_application.app_engine.project}/iap_web/appengine-${google_app_engine_application.app_engine.app_id}"
}

# Add the App Engine Service Account as an Object Viewer and Artifact Registry reader for deployments.
resource "google_project_iam_member" "app_engine_object_viewer" {
  project = google_app_engine_application.app_engine.project
  member  = "serviceAccount:${google_app_engine_application.app_engine.project}@appspot.gserviceaccount.com"
  role    = "roles/storage.objectViewer"
}

resource "google_project_iam_member" "app_engine_ar_reader" {
  project = google_app_engine_application.app_engine.project
  member  = "serviceAccount:${google_app_engine_application.app_engine.project}@appspot.gserviceaccount.com"
  role    = "roles/artifactregistry.reader"
}
