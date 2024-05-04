# bucket to upload cloud function source code
resource "google_storage_bucket" "default" {
  name                        = "${var.project}-gcf-source"
  location                    = "US"
  uniform_bucket_level_access = true
  project                     = var.project
}

# a publicly accessible bucket to share documents with end user
resource "google_storage_bucket" "public_bucket" {
  force_destroy               = false
  location                    = "US"
  name                        = "${var.project}_public_bucket"
  project                     = var.project
  public_access_prevention    = "inherited"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "public_bucket_member" {
  bucket = google_storage_bucket.public_bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

##########[start] REPEAT FOR EACH CF###################

data "archive_file" "account-health-summarisation-optimised" {
  type        = "zip"
  output_path = "/tmp/account-health-summarisation-optimised.zip"
  source_dir  = "functions/account-health-summarisation-optimised/"
}
resource "google_storage_bucket_object" "object" {
  name   = "account-health-summarisation-optimised.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.account-health-summarisation-optimised.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "account-health-summarisation-optimised" {
  name        = "account-health-summarisation-optimised"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "2Gi"
    timeout_seconds    = 60
    available_cpu      = 4
    # #service_account_email = var.#service_account_email
  }
}
resource "google_cloud_run_service_iam_member" "member_account-health-summarisation-optimised" {
  location = google_cloudfunctions2_function.account-health-summarisation-optimised.location
  service  = google_cloudfunctions2_function.account-health-summarisation-optimised.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

##########[end] REPEAT FOR EACH CF###################

data "archive_file" "account-health-tips" {
  type        = "zip"
  output_path = "/tmp/account-health-tips.zip"
  source_dir  = "functions/account-health-tips/"
}
resource "google_storage_bucket_object" "object_account-health-tips" {
  name   = "account-health-tips.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.account-health-tips.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "account-health-tips" {
  name        = "account-health-tips"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_account-health-tips.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "256Mi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_account-health-tips" {
  location = google_cloudfunctions2_function.account-health-tips.location
  service  = google_cloudfunctions2_function.account-health-tips.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "check-cust-id-in-database" {
  type        = "zip"
  output_path = "/tmp/check-cust-id-in-database.zip"
  source_dir  = "functions/check-cust-id-in-database/"
}
resource "google_storage_bucket_object" "object_check-cust-id-in-database" {
  name   = "check-cust-id-in-database.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.check-cust-id-in-database.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "check-cust-id-in-database" {
  name        = "check-cust-id-in-database"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_check-cust-id-in-database.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "256Mi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_check-cust-id-in-database" {
  location = google_cloudfunctions2_function.check-cust-id-in-database.location
  service  = google_cloudfunctions2_function.check-cust-id-in-database.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}


###################################################################################
data "archive_file" "create_fd" {
  type        = "zip"
  output_path = "/tmp/create_fd.zip"
  source_dir  = "functions/create_fd/"
}
resource "google_storage_bucket_object" "object_create_fd" {
  name   = "create_fd.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.create_fd.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "create_fd" {
  name        = "create-fd"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_create_fd.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60
  }
}
resource "google_cloud_run_service_iam_member" "member_create_fd" {
  location = google_cloudfunctions2_function.create_fd.location
  service  = google_cloudfunctions2_function.create_fd.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "event-recommendation" {
  type        = "zip"
  output_path = "/tmp/event-recommendation.zip"
  source_dir  = "functions/event-recommendation/"
}
resource "google_storage_bucket_object" "object_event-recommendation" {
  name   = "event-recommendation.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.event-recommendation.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "event-recommendation" {
  name        = "event-recommendation"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_event-recommendation.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60
  }
}
resource "google_cloud_run_service_iam_member" "member_event-recommendation" {
  location = google_cloudfunctions2_function.event-recommendation.location
  service  = google_cloudfunctions2_function.event-recommendation.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}


###################################################################################
data "archive_file" "travel-event-recommendation" {
  type        = "zip"
  output_path = "/tmp/travel-event-recommendation.zip"
  source_dir  = "functions/travel-event-recommendation/"
}
resource "google_storage_bucket_object" "object_travel-event-recommendation" {
  name   = "travel-event-recommendation.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.travel-event-recommendation.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "travel-event-recommendation" {
  name        = "travel-event-recommendation"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_travel-event-recommendation.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "512Mi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_travel-event-recommendation" {
  location = google_cloudfunctions2_function.travel-event-recommendation.location
  service  = google_cloudfunctions2_function.travel-event-recommendation.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}


###################################################################################
data "archive_file" "expense-prediction" {
  type        = "zip"
  output_path = "/tmp/expense-prediction.zip"
  source_dir  = "functions/expense-prediction/"
}
resource "google_storage_bucket_object" "object_expense-prediction" {
  name   = "expense-prediction.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.expense-prediction.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "expense-prediction" {
  name        = "expense-prediction"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_expense-prediction.name
      }
    }
    environment_variables = {
      PROJECT_ID    = var.project
      PUBLIC_BUCKET = "${var.project}_public_bucket" #the public bucket created for this project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "512Mi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_expense-prediction" {
  location = google_cloudfunctions2_function.expense-prediction.location
  service  = google_cloudfunctions2_function.expense-prediction.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "extend-overdraft" {
  type        = "zip"
  output_path = "/tmp/extend-overdraft.zip"
  source_dir  = "functions/extend-overdraft/"
}
resource "google_storage_bucket_object" "object_extend-overdraft" {
  name   = "extend-overdraft.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.extend-overdraft.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "extend-overdraft" {
  name        = "extend-overdraft"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_extend-overdraft.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "512Mi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_extend-overdraft" {
  location = google_cloudfunctions2_function.extend-overdraft.location
  service  = google_cloudfunctions2_function.extend-overdraft.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "fd_confirmation" {
  type        = "zip"
  output_path = "/tmp/fd_confirmation.zip"
  source_dir  = "functions/fd_confirmation/"
}
resource "google_storage_bucket_object" "object_fd_confirmation" {
  name   = "fd_confirmation.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.fd_confirmation.output_path # Add path to the zipped function source code
  # project     = var.project
}
resource "google_storage_bucket_object" "tnc_image" {
  name         = "tnc.jpeg"
  source       = "files/tnc.jpeg"
  content_type = "image/jpeg"
  bucket       = google_storage_bucket.public_bucket.id
}

resource "google_storage_bucket_object" "fd_tnc_doc" {
  name         = "FD_TnC.pdf"
  source       = "files/FD_TnC.pdf"
  content_type = "application/pdf"
  bucket       = google_storage_bucket.public_bucket.id
}

resource "google_cloudfunctions2_function" "fd_confirmation" {
  name        = "fd-confirmation"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_fd_confirmation.name
      }
    }
    environment_variables = {
      PROJECT_ID    = var.project
      PUBLIC_BUCKET = "${var.project}_public_bucket"
      TNC_IMAGE     = "tnc.jpeg"
      FD_TNC_DOC    = "FD_TnC.pdf"
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_fd_confirmation" {
  location = google_cloudfunctions2_function.fd_confirmation.location
  service  = google_cloudfunctions2_function.fd_confirmation.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "fd_recommendation" {
  type        = "zip"
  output_path = "/tmp/fd_recommendation.zip"
  source_dir  = "functions/fd_recommendation/"
}
resource "google_storage_bucket_object" "object_fd_recommendation" {
  name   = "fd_recommendation.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.fd_recommendation.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "fd_recommendation" {
  name        = "fd-recommendation"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_fd_recommendation.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "512Mi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_fd_recommendation" {
  location = google_cloudfunctions2_function.fd_recommendation.location
  service  = google_cloudfunctions2_function.fd_recommendation.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "fd_tenure" {
  type        = "zip"
  output_path = "/tmp/fd_tenure.zip"
  source_dir  = "functions/fd_tenure/"
}
resource "google_storage_bucket_object" "object_fd_tenure" {
  name   = "fd_tenure.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.fd_tenure.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "fd_tenure" {
  name        = "fd-tenure"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_fd_tenure.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_fd_tenure" {
  location = google_cloudfunctions2_function.fd_tenure.location
  service  = google_cloudfunctions2_function.fd_tenure.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "find_nearest_bike_dealer" {
  type        = "zip"
  output_path = "/tmp/find_nearest_bike_dealer.zip"
  source_dir  = "functions/find_nearest_bike_dealer/"
}
resource "google_storage_bucket_object" "object_find_nearest_bike_dealer" {
  name   = "find_nearest_bike_dealer.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.find_nearest_bike_dealer.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "find_nearest_bike_dealer" {
  name        = "find-nearest-bike-dealer"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_find_nearest_bike_dealer.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_find_nearest_bike_dealer" {
  location = google_cloudfunctions2_function.find_nearest_bike_dealer.location
  service  = google_cloudfunctions2_function.find_nearest_bike_dealer.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "find_nearest_car_dealers" {
  type        = "zip"
  output_path = "/tmp/find_nearest_car_dealers.zip"
  source_dir  = "functions/find_nearest_car_dealers/"
}
resource "google_storage_bucket_object" "object_find_nearest_car_dealers" {
  name   = "find_nearest_car_dealers.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.find_nearest_car_dealers.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "find_nearest_car_dealers" {
  name        = "find-nearest-car-dealers"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_find_nearest_car_dealers.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_find_nearest_car_dealers" {
  location = google_cloudfunctions2_function.find_nearest_car_dealers.location
  service  = google_cloudfunctions2_function.find_nearest_car_dealers.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "fixed-deposit-recommendation" {
  type        = "zip"
  output_path = "/tmp/fixed-deposit-recommendation.zip"
  source_dir  = "functions/fixed-deposit-recommendation/"
}
resource "google_storage_bucket_object" "object_fixed-deposit-recommendation" {
  name   = "fixed-deposit-recommendation.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.fixed-deposit-recommendation.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "fixed-deposit-recommendation" {
  name        = "fixed-deposit-recommendation"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_fixed-deposit-recommendation.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_fixed-deposit-recommendation" {
  location = google_cloudfunctions2_function.fixed-deposit-recommendation.location
  service  = google_cloudfunctions2_function.fixed-deposit-recommendation.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}


###################################################################################
data "archive_file" "get-account-balance" {
  type        = "zip"
  output_path = "/tmp/get-account-balance.zip"
  source_dir  = "functions/get-account-balance/"
}
resource "google_storage_bucket_object" "object_get-account-balance" {
  name   = "get-account-balance.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.get-account-balance.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "get-account-balance" {
  name        = "get-account-balance"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_get-account-balance.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_get-account-balance" {
  location = google_cloudfunctions2_function.get-account-balance.location
  service  = google_cloudfunctions2_function.get-account-balance.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "get_anomaly_transaction" {
  type        = "zip"
  output_path = "/tmp/get_anomaly_transaction.zip"
  source_dir  = "functions/get_anomaly_transaction/"
}
resource "google_storage_bucket_object" "object_get_anomaly_transaction" {
  name   = "get_anomaly_transaction.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.get_anomaly_transaction.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "get_anomaly_transaction" {
  name        = "get-anomaly-transaction"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_get_anomaly_transaction.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_get_anomaly_transaction" {
  location = google_cloudfunctions2_function.get_anomaly_transaction.location
  service  = google_cloudfunctions2_function.get_anomaly_transaction.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "get_category_wise_expenditure" {
  type        = "zip"
  output_path = "/tmp/get_category_wise_expenditure.zip"
  source_dir  = "functions/get_category_wise_expenditure/"
}
resource "google_storage_bucket_object" "object_get_category_wise_expenditure" {
  name   = "get_category_wise_expenditure.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.get_category_wise_expenditure.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "get_category_wise_expenditure" {
  name        = "get-category-wise-expenditure"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_get_category_wise_expenditure.name
      }
    }
    environment_variables = {
      PROJECT_ID    = var.project
      PUBLIC_BUCKET = "${var.project}_public_bucket"
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_get_category_wise_expenditure" {
  location = google_cloudfunctions2_function.get_category_wise_expenditure.location
  service  = google_cloudfunctions2_function.get_category_wise_expenditure.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "get_return_of_investment" {
  type        = "zip"
  output_path = "/tmp/get_return_of_investment.zip"
  source_dir  = "functions/get_return_of_investment/"
}
resource "google_storage_bucket_object" "object_get_return_of_investment" {
  name   = "get_return_of_investment.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.get_return_of_investment.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "get_return_of_investment" {
  name        = "get-return-of-investment"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_get_return_of_investment.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_get_return_of_investment" {
  location = google_cloudfunctions2_function.get_return_of_investment.location
  service  = google_cloudfunctions2_function.get_return_of_investment.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "get_travel_dates" {
  type        = "zip"
  output_path = "/tmp/get_travel_dates.zip"
  source_dir  = "functions/get_travel_dates/"
}
resource "google_storage_bucket_object" "object_get_travel_dates" {
  name   = "get_travel_dates.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.get_travel_dates.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "get_travel_dates" {
  name        = "get-travel-dates"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_get_travel_dates.name
      }
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_get_travel_dates" {
  location = google_cloudfunctions2_function.get_travel_dates.location
  service  = google_cloudfunctions2_function.get_travel_dates.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}


###################################################################################
data "archive_file" "high_risk_mutual_funds" {
  type        = "zip"
  output_path = "/tmp/high_risk_mutual_funds.zip"
  source_dir  = "functions/high_risk_mutual_funds/"
}
resource "google_storage_bucket_object" "object_high_risk_mutual_funds" {
  name   = "high_risk_mutual_funds.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.high_risk_mutual_funds.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "high_risk_mutual_funds" {
  name        = "high-risk-mutual-funds"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_high_risk_mutual_funds.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_high_risk_mutual_funds" {
  location = google_cloudfunctions2_function.high_risk_mutual_funds.location
  service  = google_cloudfunctions2_function.high_risk_mutual_funds.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "how_my_debt_funds_doing" {
  type        = "zip"
  output_path = "/tmp/how_my_debt_funds_doing.zip"
  source_dir  = "functions/how_my_debt_funds_doing/"
}
resource "google_storage_bucket_object" "object_how_my_debt_funds_doing" {
  name   = "how_my_debt_funds_doing.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.how_my_debt_funds_doing.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_storage_bucket_object" "market_summary_doc" {
  name         = "Market_Summary.pdf"
  source       = "files/Market_Summary.pdf"
  content_type = "application/pdf"
  bucket       = google_storage_bucket.public_bucket.id
}

resource "google_cloudfunctions2_function" "how_my_debt_funds_doing" {
  name        = "how-my-debt-funds-doing"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_how_my_debt_funds_doing.name
      }
    }
    environment_variables = {
      PROJECT_ID      = var.project
      PUBLIC_BUCKET   = "${var.project}_public_bucket"
      MARKET_SUMM_DOC = "Market_Summary.pdf"
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_how_my_debt_funds_doing" {
  location = google_cloudfunctions2_function.how_my_debt_funds_doing.location
  service  = google_cloudfunctions2_function.how_my_debt_funds_doing.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "how_my_mutual_fund_doing" {
  type        = "zip"
  output_path = "/tmp/how_my_mutual_fund_doing.zip"
  source_dir  = "functions/how_my_mutual_fund_doing/"
}
resource "google_storage_bucket_object" "object_how_my_mutual_fund_doing" {
  name   = "how_my_mutual_fund_doing.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.how_my_mutual_fund_doing.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "how_my_mutual_fund_doing" {
  name        = "how-my-mutual-fund-doing"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_how_my_mutual_fund_doing.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "512Mi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_how_my_mutual_fund_doing" {
  location = google_cloudfunctions2_function.how_my_mutual_fund_doing.location
  service  = google_cloudfunctions2_function.how_my_mutual_fund_doing.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "is_in_india" {
  type        = "zip"
  output_path = "/tmp/is_in_india.zip"
  source_dir  = "functions/is_in_india/"
}
resource "google_storage_bucket_object" "object_is_in_india" {
  name   = "is_in_india.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.is_in_india.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "is_in_india" {
  name        = "is-in-india"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_is_in_india.name
      }
    }
    environment_variables = {
      PROJECT_ID   = var.project
      MAPS_API_KEY = var.maps_api_key
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "512Mi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_is_in_india" {
  location = google_cloudfunctions2_function.is_in_india.location
  service  = google_cloudfunctions2_function.is_in_india.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "set_destination" {
  type        = "zip"
  output_path = "/tmp/set_destination.zip"
  source_dir  = "functions/set_destination/"
}
resource "google_storage_bucket_object" "object_set_destination" {
  name   = "set_destination.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.set_destination.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "set_destination" {
  name        = "set-destination"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_set_destination.name
      }
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_set_destination" {
  location = google_cloudfunctions2_function.set_destination.location
  service  = google_cloudfunctions2_function.set_destination.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "set_fd_amount" {
  type        = "zip"
  output_path = "/tmp/set_fd_amount.zip"
  source_dir  = "functions/set_fd_amount/"
}
resource "google_storage_bucket_object" "object_set_fd_amount" {
  name   = "set_fd_amount.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.set_fd_amount.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "set_fd_amount" {
  name        = "set-fd-amount"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_set_fd_amount.name
      }
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_set_fd_amount" {
  location = google_cloudfunctions2_function.set_fd_amount.location
  service  = google_cloudfunctions2_function.set_fd_amount.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "rag_qa_chain_2" {
  type        = "zip"
  output_path = "/tmp/rag_qa_chain_2.zip"
  source_dir  = "functions/rag_qa_chain_2/"
}
resource "google_storage_bucket_object" "object_rag_qa_chain_2" {
  name   = "rag_qa_chain_2.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.rag_qa_chain_2.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "rag_qa_chain_2" {
  name        = "rag-qa-chain-2"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_rag_qa_chain_2.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "2Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_rag_qa_chain_2" {
  location = google_cloudfunctions2_function.rag_qa_chain_2.location
  service  = google_cloudfunctions2_function.rag_qa_chain_2.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "recommend_debt_funds" {
  type        = "zip"
  output_path = "/tmp/recommend_debt_funds.zip"
  source_dir  = "functions/recommend_debt_funds/"
}
resource "google_storage_bucket_object" "object_recommend_debt_funds" {
  name   = "recommend_debt_funds.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.recommend_debt_funds.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "recommend_debt_funds" {
  name        = "recommend-debt-funds"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_recommend_debt_funds.name
      }
    }
    environment_variables = {
      PROJECT_ID      = var.project
      PUBLIC_BUCKET   = "${var.project}_public_bucket"
      MARKET_SUMM_DOC = "Market_Summary.pdf"
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_recommend_debt_funds" {
  location = google_cloudfunctions2_function.recommend_debt_funds.location
  service  = google_cloudfunctions2_function.recommend_debt_funds.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "recommend_mutual_fund" {
  type        = "zip"
  output_path = "/tmp/recommend_mutual_fund.zip"
  source_dir  = "functions/recommend_mutual_fund/"
}
resource "google_storage_bucket_object" "object_recommend_mutual_fund" {
  name   = "recommend_mutual_fund.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.recommend_mutual_fund.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "recommend_mutual_fund" {
  name        = "recommend-mutual-fund"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_recommend_mutual_fund.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_recommend_mutual_fund" {
  location = google_cloudfunctions2_function.recommend_mutual_fund.location
  service  = google_cloudfunctions2_function.recommend_mutual_fund.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "tenure_validation" {
  type        = "zip"
  output_path = "/tmp/tenure_validation.zip"
  source_dir  = "functions/tenure_validation/"
}
resource "google_storage_bucket_object" "object_tenure_validation" {
  name   = "tenure_validation.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.tenure_validation.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "tenure_validation" {
  name        = "tenure-validation"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_tenure_validation.name
      }
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_tenure_validation" {
  location = google_cloudfunctions2_function.tenure_validation.location
  service  = google_cloudfunctions2_function.tenure_validation.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "travel_card_recommendation" {
  type        = "zip"
  output_path = "/tmp/travel_card_recommendation.zip"
  source_dir  = "functions/travel_card_recommendation/"
}
resource "google_storage_bucket_object" "object_travel_card_recommendation" {
  name   = "travel_card_recommendation.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.travel_card_recommendation.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "travel_card_recommendation" {
  name        = "travel-card-recommendation"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_travel_card_recommendation.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_travel_card_recommendation" {
  location = google_cloudfunctions2_function.travel_card_recommendation.location
  service  = google_cloudfunctions2_function.travel_card_recommendation.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}
###################################################################################
data "archive_file" "unusual_spends" {
  type        = "zip"
  output_path = "/tmp/unusual_spends.zip"
  source_dir  = "functions/unusual_spends/"
}
resource "google_storage_bucket_object" "object_unusual_spends" {
  name   = "unusual_spends.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.unusual_spends.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "unusual_spends" {
  name        = "unusual-spends"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_unusual_spends.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_unusual_spends" {
  location = google_cloudfunctions2_function.unusual_spends.location
  service  = google_cloudfunctions2_function.unusual_spends.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}
###################################################################################
data "archive_file" "upload_credit_card" {
  type        = "zip"
  output_path = "/tmp/upload_credit_card.zip"
  source_dir  = "functions/upload_credit_card/"
}
resource "google_storage_bucket_object" "object_upload_credit_card" {
  name   = "upload_credit_card.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.upload_credit_card.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "upload_credit_card" {
  name        = "upload-credit-card"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_upload_credit_card.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_upload_credit_card" {
  location = google_cloudfunctions2_function.upload_credit_card.location
  service  = google_cloudfunctions2_function.upload_credit_card.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}
###################################################################################
data "archive_file" "translation-handler-cymbal-bank" {
  type        = "zip"
  output_path = "/tmp/translation-handler-cymbal-bank.zip"
  source_dir  = "functions/translation-handler-cymbal-bank/"
}
resource "google_storage_bucket_object" "object_translation-handler-cymbal-bank" {
  name   = "translation-handler-cymbal-bank.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.translation-handler-cymbal-bank.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "translation-handler-cymbal-bank" {
  name        = "translation-handler-cymbal-bank"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_translation-handler-cymbal-bank.name
      }
    }
    environment_variables = {
      PROJECT_ID              = var.project
      CATEGORIZE_EXPENSE_URL  = google_cloudfunctions2_function.get_category_wise_expenditure.url
      SET_DEFAULT_PARAM_URL   = ""
      RAG_QA_CHAIN_URL        = google_cloudfunctions2_function.rag_qa_chain_2.url
      ACCOUNT_SUMMARY_URL     = google_cloudfunctions2_function.account-health-summarisation-optimised.url
      ACCOUNT_BALANCE_URL     = google_cloudfunctions2_function.get-account-balance.url
      ACCOUNT_TIPS_URL        = google_cloudfunctions2_function.account-health-tips.url
      CREDIT_CARD_RECOMM_URL  = google_cloudfunctions2_function.travel_card_recommendation.url
      CREDIT_CARD_CREATE_URL  = google_cloudfunctions2_function.upload_credit_card.url
      DEBT_FUND_URL           = google_cloudfunctions2_function.how_my_debt_funds_doing.url
      EVENT_RECOMM_URL        = google_cloudfunctions2_function.event-recommendation.url
      EXPENSE_PREDICT_URL     = google_cloudfunctions2_function.expense-prediction.url
      FD_RECOMM_URL           = google_cloudfunctions2_function.fd_recommendation.url
      FD_CONFIRM_URL          = google_cloudfunctions2_function.fd_confirmation.url
      FD_TENURE_URL           = google_cloudfunctions2_function.fd_tenure.url
      HIGH_RISK_MF_URL        = google_cloudfunctions2_function.high_risk_mutual_funds.url
      MF_RECOMM_URL           = google_cloudfunctions2_function.recommend_mutual_fund.url
      FD_CREATE_URL           = google_cloudfunctions2_function.create_fd.url
      DEBT_FUND_RECOMM_URL    = google_cloudfunctions2_function.recommend_debt_funds.url
      UNUSUAL_EXPENSE_URL     = google_cloudfunctions2_function.unusual_spends.url
      FIND_NEAREST_DEALER_URL = google_cloudfunctions2_function.find_nearest_car_dealers.url
      TRAVEL_EVENT_RECOMM_URL = google_cloudfunctions2_function.travel-event-recommendation.url
      FD_TENURE_VAL_URL       = google_cloudfunctions2_function.tenure_validation.url
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_translation-handler-cymbal-bank" {
  location = google_cloudfunctions2_function.translation-handler-cymbal-bank.location
  service  = google_cloudfunctions2_function.translation-handler-cymbal-bank.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "credit-card-imagen" {
  type        = "zip"
  output_path = "/tmp/credit-card-imagen.zip"
  source_dir  = "functions/credit-card-imagen/"
}
resource "google_storage_bucket_object" "object_credit-card-imagen" {
  name   = "credit-card-imagen.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.credit-card-imagen.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "credit-card-imagen" {
  name        = "credit-card-imagen"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_credit-card-imagen.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
      LOCATION   = "us-central1"
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_credit-card-imagen" {
  location = google_cloudfunctions2_function.credit-card-imagen.location
  service  = google_cloudfunctions2_function.credit-card-imagen.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "user-login" {
  type        = "zip"
  output_path = "/tmp/user-login.zip"
  source_dir  = "functions/user-login/"
}
resource "google_storage_bucket_object" "object_user-login" {
  name   = "user-login.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.user-login.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "user-login" {
  name        = "user-login"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_user-login.name
      }
    }
    environment_variables = {
      PROJECT_ID = var.project
      LOCATION   = "us-central1"
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "1Gi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_user-login" {
  location = google_cloudfunctions2_function.user-login.location
  service  = google_cloudfunctions2_function.user-login.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}

###################################################################################
data "archive_file" "translate" {
  type        = "zip"
  output_path = "/tmp/translate.zip"
  source_dir  = "functions/translate/"
}
resource "google_storage_bucket_object" "object_translate" {
  name   = "translate.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.translate.output_path # Add path to the zipped function source code
  # project     = var.project
}

resource "google_cloudfunctions2_function" "translate" {
  name        = "translate"
  location    = "us-central1"
  description = "function which gives account health and summary"
  project     = var.project

  build_config {
    runtime     = "python311"
    entry_point = "hello_http" # Set the entry point
    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.object_translate.name
      }
    }
    environment_variables = {
      PROJECT_ID       = var.project
      RAG_QA_CHAIN_URL = google_cloudfunctions2_function.rag_qa_chain_2.url
    }
  }

  service_config {
    min_instance_count = 1
    available_memory   = "256Mi"
    timeout_seconds    = 60

  }
}
resource "google_cloud_run_service_iam_member" "member_translate" {
  location = google_cloudfunctions2_function.translate.location
  service  = google_cloudfunctions2_function.translate.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  project  = var.project
}
