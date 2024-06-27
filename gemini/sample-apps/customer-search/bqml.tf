# Create initial training dataset for an expense prediction model
resource "google_bigquery_job" "create_training_data_expense_pred" {
  job_id  = "job_create_training_data_expense_pred-${var.project}_v2"
  project = var.project
  labels = {
    "example-label" = "example-value"
  }

  query {
    query = "SELECT ac_id, DATE_TRUNC(date, MONTH) AS month_year ,sub_category,category,sum(transaction_amount) as transaction_amount FROM `${var.project}.DummyBankDataset.AccountTransactions` WHERE debit_credit_indicator = 'Debit' GROUP BY ac_id,sub_category,category, month_year"

    destination_table {
      table_id = google_bigquery_table.training_data.id
    }

    allow_large_results = true
    flatten_results     = true

    script_options {
      key_result_statement = "LAST"
    }
  }
}

# BQML models will be created using a colab notebook. 
# Creation of a colab runtime requires a vpc with a subnetwork.

resource "google_compute_network" "vpc_network" {
  project                                   = var.project
  name                                      = "vpc-network"
  auto_create_subnetworks                   = false
  network_firewall_policy_enforcement_order = "BEFORE_CLASSIC_FIREWALL"
}

resource "google_compute_subnetwork" "subnetwork_vpc" {
  project                  = var.project
  name                     = "subnetwork-vpc"
  ip_cidr_range            = "10.0.0.0/22"
  network                  = google_compute_network.vpc_network.id
  private_ip_google_access = true
  region                   = var.region
}