## Project we're using

# Project we're deploying to
data "google_project" "project" {
  project_id = var.project_id
}


## Configure Project APIs
resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  project            = data.google_project.project.id
  service            = each.value
  disable_on_destroy = false
}

## Enable Firebase on the project
resource "google_firebase_project" "firebase" {
  depends_on = [google_project_service.apis]
  provider   = google-beta
  project    = data.google_project.project.project_id
}

## Create a public maps API key and store it in secrets manager
# The public key is put on the client and thus has a greater risk than the server key
resource "google_apikeys_key" "maps_public" {
  depends_on   = [google_project_service.apis]
  name         = "maps-public-api"
  display_name = "Maps Public API Key"
  project      = data.google_project.project.project_id

  # Restrict API key to only what's needed
  restrictions {
    api_targets {
      service = "maps-backend.googleapis.com"
    }
    api_targets {
      service = "places-backend.googleapis.com"
    }
  }
}

## Create a server maps API key and store it in secrets manager
# The server key is never put on the client
resource "google_apikeys_key" "maps_server" {
  depends_on   = [google_project_service.apis]
  name         = "maps-server-api"
  display_name = "Maps Server API Key"
  project      = data.google_project.project.project_id

  # Restrict API key to only what's needed
  restrictions {
    api_targets {
      service = "routes.googleapis.com"
    }
    api_targets {
      service = "static-maps-backend.googleapis.com"
    }
  }
}

## Store the API key in secret manager

# Store the public key as a secret
resource "google_secret_manager_secret" "maps_public" {
  secret_id = "NEXT_PUBLIC_GOOGLE_MAPS_PUBLIC_API_KEY"
  project   = data.google_project.project.project_id

  replication {
    auto {}
  }
}
resource "google_secret_manager_secret_version" "maps_public" {
  secret      = google_secret_manager_secret.maps_public.id
  secret_data = google_apikeys_key.maps_public.key_string
}

# Store the server key as a secret
resource "google_secret_manager_secret" "maps_server" {
  secret_id = "GOOGLE_MAPS_API_SERVER_KEY"
  project   = data.google_project.project.project_id

  replication {
    auto {}
  }
}
resource "google_secret_manager_secret_version" "maps_server" {
  secret      = google_secret_manager_secret.maps_server.id
  secret_data = google_apikeys_key.maps_server.key_string
}


## Grant Firebase App Hosting SA the right permissions
resource "google_project_iam_member" "app_hosting" {
  # Only configure this if App Hosting has been setup before
  for_each = toset(var.firebase_app_hosting ? local.app_hosting_iam : [])
  project  = data.google_project.project.project_id
  role     = each.key
  member   = "serviceAccount:firebase-app-hosting-compute@${data.google_project.project.project_id}.iam.gserviceaccount.com"
}
