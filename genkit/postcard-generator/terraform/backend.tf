terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.28.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "6.28.0"
    }
  }
}
