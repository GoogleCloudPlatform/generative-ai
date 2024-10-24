locals {
  apis = [
    # Cloud Build for App Hosting
    "cloudbuild.googleapis.com",
    # Secret Manager for App Hosting
    "secretmanager.googleapis.com",
    # To configure user policies
    "iam.googleapis.com",
    # Allow creation of API keys (for maps)
    "apikeys.googleapis.com",
    # For App Hosting
    "firebase.googleapis.com",
    # To configure Org policies
    "orgpolicy.googleapis.com",
    # To generate map images
    "static-maps-backend.googleapis.com",
    # To calculate routes between places
    "routes.googleapis.com",
    # To provide autocomplete suggestions
    "maps-backend.googleapis.com",
    "places-backend.googleapis.com",
    # Vertex AI for Gemini & Imagen
    "aiplatform.googleapis.com",
    # App Hosting Repo Connect
    "developerconnect.googleapis.com",
  ]

  app_hosting_iam = [
    # Allow access to secret manager
    "roles/secretmanager.secretAccessor",
    # Allow access to Vertex AI
    "roles/aiplatform.user"
  ]
}
