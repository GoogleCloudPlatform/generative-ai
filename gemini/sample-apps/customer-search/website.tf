#The website will be hosted on Cloud Run. 
#Create the artifact registry repository to upload the website container image.

resource "google_artifact_registry_repository" "website-repo" {
  location      = "us-central1"
  repository_id = "${var.project}-website-repo"
  project       = var.project
  description   = "Website container image repository"
  format        = "DOCKER"
}