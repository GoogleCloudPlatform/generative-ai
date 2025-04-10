# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

locals {
  primary_alloy_instance_id       = "primary"
  alloy_db_user                   = "concierge"
  alloy_db_cluster_id             = "concierge-server-session"
  alloy_db_connection_secret_name = "concierge-alloy-db-connection-url"
  cymbal_dataset_id               = "cymbal_retail"
  cymbal_dataset_connection_id    = "cymbal_retail_connection"
}

# Generate a random password for the initial AlloyDB user.
resource "random_password" "alloy_db_password" {
  length  = 32
  special = false
}

# Create an AlloyDB cluster and instance for session management.
module "alloy-db" {
  source  = "GoogleCloudPlatform/alloy-db/google"
  version = "~> 3.2.0"

  cluster_id           = local.alloy_db_cluster_id
  cluster_location     = var.region
  project_id           = module.project-factory.project_id
  cluster_labels       = {}
  cluster_display_name = ""

  network_self_link = module.vpc.network.network_id

  cluster_initial_user = {
    user     = local.alloy_db_user
    password = random_password.alloy_db_password.result
  }

  automated_backup_policy = null
  read_pool_instance      = null

  primary_instance = {
    instance_id       = local.primary_alloy_instance_id
    instance_type     = "PRIMARY"
    availability_type = "ZONAL"
    machine_cpu_count = 2
    database_flags    = {}
    display_name      = "Primary instance for storing the concierge demo session data."
  }

  depends_on = [module.project-factory, module.vpc, google_service_networking_connection.google_services_connection]
}

# Add the postgres connection string for the AlloyDB instance as a secret to be used by the backend server.
module "secret-manager" {
  source     = "GoogleCloudPlatform/secret-manager/google"
  version    = "~> 0.8"
  project_id = module.project-factory.project_id
  secrets = [
    {
      name        = local.alloy_db_connection_secret_name
      secret_data = "postgresql://${local.alloy_db_user}:${random_password.alloy_db_password.result}@${module.alloy-db.primary_instance.ip_address}:5432/postgres"
    },
  ]
  secret_accessors_list = [
    "serviceAccount:${module.concierge_server_service_account.email}"
  ]
}

# Create a BigQuery dataset for the mock Cymbal Retail data and embedding model.
resource "google_bigquery_dataset" "cymbal_retail_dataset" {
  project       = module.project-factory.project_id
  dataset_id    = local.cymbal_dataset_id
  friendly_name = "Cymbal Retail Mock Dataset"
  description   = "This is a mock dataset containing fake retail data. Used for grounding a Gen AI chat application."
  location      = var.bigquery_dataset_location

  access {
    role          = "OWNER"
    user_by_email = module.concierge_server_service_account.email
  }

  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }
}

# Create a remote Cloud Resource Connection to enable access to BQML Embedding models
resource "google_bigquery_connection" "cymbal_connection" {
  project       = module.project-factory.project_id
  connection_id = local.cymbal_dataset_connection_id
  location      = var.bigquery_dataset_location
  cloud_resource {}
}

# Add the BigQuery Connection Service Account as a Vertex AI User. Enables creation of embedding models.
# Note: If this fails during initial creation, wait a few minutes and try again as it may take a few minutes for the Service Account to be created.
resource "google_project_iam_member" "cymbal_connection_vertex_user" {
  project = module.project-factory.project_id
  role    = "roles/aiplatform.user"

  member = "serviceAccount:${google_bigquery_connection.cymbal_connection.cloud_resource[0].service_account_id}"
}
