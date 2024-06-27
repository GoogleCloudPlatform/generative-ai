##########[start]Create a firebase webapp for authenticating users to the website############# 

resource "google_firebase_project" "auth" {
  provider = google-beta
  project  = var.project
  depends_on = [
    google_project_service.init,
  ]
}

# Creates an Identity Platform config.
# Also enables Firebase Authentication with Identity Platform in the project if not.
resource "google_identity_platform_config" "auth" {
  provider = google-beta
  project  = var.project

  # Auto-deletes anonymous users
  autodelete_anonymous_users = true

  # Configures local sign-in methods, like anonymous, email/password, and phone authentication.
  sign_in {
    allow_duplicate_emails = true

    anonymous {
      enabled = true
    }

    email {
      enabled           = true
      password_required = false
    }

  }
  # Configures a temporary quota for new signups for anonymous, email/password, and phone number.
  quota {
    sign_up_quota_config {
      quota          = 1000
      start_time     = ""
      quota_duration = "7200s"
    }
  }

  depends_on = [
    google_project_service.auth,
  ]
}

resource "google_firebase_web_app" "auth" {
  provider     = google-beta
  project      = var.project
  display_name = "My Web app"

  # The other App types (Android and Apple) use "DELETE" by default.
  # Web apps don't use "DELETE" by default due to backward-compatibility.
  deletion_policy = "DELETE"

  # Wait for Firebase to be enabled in the Google Cloud project before creating this App.
  depends_on = [
    google_firebase_project.auth,
  ]
}

##########[end]Create a firebase webapp for authenticating users to the website############# 
