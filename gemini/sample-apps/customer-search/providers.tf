terraform {
  required_version = "~>1.6.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~>5.24.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~>5.24.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~>2.4.2"
    }
  }
}

provider "google-beta" {
  alias                 = "no_user_project_override"
  user_project_override = false
}