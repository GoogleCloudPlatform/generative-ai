
## Deploy Image Processor

# Grant access to the Pub/Sub account
resource "google_service_account_iam_member" "allow_firestore_eventarc" {
  service_account_id = google_service_account.image_processor_trigger.id
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

## Package up Image Processor function
data "archive_file" "image_processor" {
  type             = "zip"
  output_path      = "${path.root}/resources/artifacts/image-processor.zip"
  output_file_mode = "0666"

  source_dir = "${path.root}/../image-processor-function"

  excludes = [
    ".env",
    "node_modules",
    "*.md",
    "lib",
    ".genkit",
  ]
}

resource "google_storage_bucket_object" "image_processor" {
  name   = "image-processor.zip"
  bucket = google_storage_bucket.build.name
  source = data.archive_file.image_processor.output_path
}

resource "google_cloudfunctions2_function" "image_processor" {
  name        = "image-processor"
  location    = var.location
  description = "Image Processor Function"
  project     = data.google_project.project.project_id

  build_config {
    runtime     = "python312"
    entry_point = "image_processor"
    source {
      storage_source {
        bucket = google_storage_bucket.build.name
        object = google_storage_bucket_object.image_processor.name
      }
    }
    service_account = "projects/${data.google_project.project.project_id}/serviceAccounts/${google_service_account.image_processor_image_processor_build.email}"
  }

  service_config {
    available_memory      = "1G"
    available_cpu         = "1"
    service_account_email = google_service_account.image_processor_image_processorfunction.email
  }

  event_trigger {
    event_type            = "google.cloud.firestore.document.v1.written"
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.image_processor_trigger.email
    trigger_region        = lower(var.firestore_location)
    event_filters {
      attribute = "database"
      value     = "(default)"
    }
    event_filters {
      attribute = "document"
      value     = "screenshots/*"
      operator  = "match-path-pattern"
    }
  }
}

# Allow Eventarc trigger to invoke image-processor
resource "google_cloud_run_service_iam_member" "image_processor_trigger" {
  project  = data.google_project.project.project_id
  location = google_cloudfunctions2_function.image_processor.location
  service  = google_cloudfunctions2_function.image_processor.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.image_processor_trigger.email}"
}
