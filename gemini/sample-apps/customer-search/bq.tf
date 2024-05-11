resource "google_storage_bucket" "bq_tables" {
  name                        = "${var.project}-bq-tables-csv" # Every bucket name must be globally unique
  location                    = "US"
  uniform_bucket_level_access = true
  project                     = var.project
}
#################[start] BQ datasets###################
resource "google_bigquery_dataset" "dummybankdataset" {
  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }
  access {
    role          = "OWNER"
    user_by_email = var.user_email
  }
  access {
    role          = "READER"
    special_group = "projectReaders"
  }
  access {
    role          = "WRITER"
    special_group = "projectWriters"
  }
  dataset_id                 = "DummyBankDataset"
  delete_contents_on_destroy = false
  location                   = "US"
  project                    = var.project
}
resource "google_bigquery_dataset" "expenseprediction" {
  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }
  access {
    role          = "OWNER"
    user_by_email = var.user_email
  }
  access {
    role          = "READER"
    special_group = "projectReaders"
  }
  access {
    role          = "WRITER"
    special_group = "projectWriters"
  }
  dataset_id                 = "ExpensePrediction"
  delete_contents_on_destroy = false
  location                   = "US"
  project                    = var.project
}

#################[end] BQ datasets #########################################

#################[start] BQ tables #########################################

# upload table data to gcs bucket
resource "google_storage_bucket_object" "account" {
  name         = "account.csv"
  content_type = "csv"
  source       = "files/tables/account.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

# create the table by defining the schema
resource "google_bigquery_table" "account" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"customer_id\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"account_id\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"product\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"account_open_date\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"avg_monthly_bal\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"min_balance\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"default_status\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"account_close_date\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"last_payment_date\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"last_payment_amount\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"maturity_date\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"banking_partner_acc_flag\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Banking_Partner_Name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Last_Due\",\"type\":\"STRING\"},{\"name\":\"current_balance\",\"type\":\"FLOAT\"}]"
  table_id   = "Account"
}

# load the table data from gcs to BQ
resource "google_bigquery_job" "loading_data_to_account_table" {
  depends_on = [google_bigquery_table.account, google_storage_bucket_object.account]
  project    = var.project
  job_id     = "job-loading_data_to_account_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/account.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.account.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "accounttransactions" {
  name         = "accounttransactions.csv"
  content_type = "csv"
  source       = "files/tables/accounttransactions.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "accounttransactions" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"ac_id\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"date\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"debit_credit_indicator\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"transaction_category\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"transaction_type\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"transaction_amount\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"disputed_transaction_indicator\",\"type\":\"BOOLEAN\"},{\"mode\":\"NULLABLE\",\"name\":\"failed_transaction_indicator\",\"type\":\"BOOLEAN\"},{\"mode\":\"NULLABLE\",\"name\":\"counterparty_name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"description\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"category\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"sub_category\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"country\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"city\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"transaction_id\",\"type\":\"INTEGER\"}]"
  table_id   = "AccountTransactions"
}

resource "google_bigquery_job" "loading_data_to_accounttransactions_table" {
  depends_on = [google_bigquery_table.accounttransactions, google_storage_bucket_object.accounttransactions]
  project    = var.project
  job_id     = "job-loading_data_to_accounttransactions_table-${var.project}_v2"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/accounttransactions.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.accounttransactions.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "cardealers" {
  name         = "cardealers.csv"
  content_type = "csv"
  source       = "files/tables/cardealers.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "cardealers" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"brand\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"dealer_name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"address\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"category\",\"type\":\"STRING\"}]"
  table_id   = "CarDealers"
}

resource "google_bigquery_job" "loading_data_to_cardealers_table" {
  depends_on = [google_bigquery_table.cardealers, google_storage_bucket_object.cardealers]
  project    = var.project
  job_id     = "job-loading_data_to_cardealers_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/cardealers.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.cardealers.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "carloan" {
  name         = "carloan.csv"
  content_type = "csv"
  source       = "files/tables/carloan.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "carloan" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"cic_score_min\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"cic_score_max\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"roi_3_to_5\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"roi_above_5\",\"type\":\"FLOAT\"}]"
  table_id   = "CarLoan"
}

resource "google_bigquery_job" "loading_data_to_carloan_table" {
  depends_on = [google_bigquery_table.carloan, google_storage_bucket_object.carloan]
  project    = var.project
  job_id     = "job-loading_data_to_carloan_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/carloan.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.carloan.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "creditcards" {
  name         = "creditcards.csv"
  content_type = "csv"
  source       = "files/tables/creditcards.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "creditcards" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"name\":\"customer_id\",\"type\":\"INTEGER\"},{\"name\":\"credit_card_number\",\"type\":\"INTEGER\"},{\"name\":\"credit_card_expiration_month\",\"type\":\"INTEGER\"},{\"name\":\"credit_card_expiration_year\",\"type\":\"INTEGER\"},{\"name\":\"credit_card_name\",\"type\":\"STRING\"},{\"name\":\"credit_card_last_updated\",\"type\":\"DATE\"},{\"defaultValueExpression\":\"10000\",\"name\":\"transaction_limit\",\"type\":\"FLOAT\"},{\"defaultValueExpression\":\"false\",\"name\":\"international_transaction_enabled\",\"type\":\"BOOLEAN\"}]"
  table_id   = "CreditCards"
}
resource "google_bigquery_job" "loading_data_to_creditcards_table" {
  depends_on = [google_bigquery_table.creditcards, google_storage_bucket_object.creditcards]
  project    = var.project
  job_id     = "job-loading_data_to_creditcards_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/creditcards.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.creditcards.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "customer" {
  name         = "customer.csv"
  content_type = "csv"
  source       = "files/tables/customer.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "customer" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"customer_id\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"First_Name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"middle_name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Last_Name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"date_of_birth\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"Address_1st_Line\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Address_2nd_Line\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Address_3rd_Line\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"city\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"state\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Plus_Code\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"occupation\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"annual_income_range\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"customer_affluence_score\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"relationship_start_date\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"age_on_book\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"employer\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"PAN\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"aadhar\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"customer_credit_risk_score\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"KYC_Status\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"churn_propensity\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"Affinities\",\"type\":\"STRING\"},{\"name\":\"credit_score\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"firebase_uid\",\"type\":\"STRING\"}]"
  table_id   = "Customer"
}
resource "google_bigquery_job" "loading_data_to_customer_table" {
  depends_on = [google_bigquery_table.customer, google_storage_bucket_object.customer]
  project    = var.project
  job_id     = "job-loading_data_to_customer_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/customer.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.customer.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "customerevents" {
  name         = "customerevents.csv"
  content_type = "csv"
  source       = "files/tables/customerevents.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "customerevents" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"event_name_\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"event_date_\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"last_date_of_invite_\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"event_type\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"event_tags_\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"location\",\"type\":\"STRING\"}]"
  table_id   = "CustomerEvents"
}
resource "google_bigquery_job" "loading_data_to_customerevents_table" {
  depends_on = [google_bigquery_table.customerevents, google_storage_bucket_object.customerevents]
  project    = var.project
  job_id     = "job-loading_data_to_customerevents_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/customerevents.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.customerevents.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "debitcards" {
  name         = "debitcards.csv"
  content_type = "csv"
  source       = "files/tables/debitcards.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "debitcards" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"REQUIRED\",\"name\":\"ac_id\",\"type\":\"INTEGER\"},{\"mode\":\"REQUIRED\",\"name\":\"debit_card_no\",\"type\":\"INTEGER\"},{\"mode\":\"REQUIRED\",\"name\":\"expiration_month\",\"type\":\"INTEGER\"},{\"mode\":\"REQUIRED\",\"name\":\"expiration_year\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"debit_card_name\",\"type\":\"STRING\"},{\"defaultValueExpression\":\"10000\",\"mode\":\"REQUIRED\",\"name\":\"transaction_limit\",\"type\":\"FLOAT\"},{\"defaultValueExpression\":\"false\",\"mode\":\"REQUIRED\",\"name\":\"international_transaction_enabled\",\"type\":\"BOOLEAN\"}]"
  table_id   = "DebitCards"
}
resource "google_bigquery_job" "loading_data_to_debitcards_table" {
  depends_on = [google_bigquery_table.debitcards, google_storage_bucket_object.debitcards]
  project    = var.project
  job_id     = "job-loading_data_to_debitcards_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/debitcards.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.debitcards.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "fdinterestrates" {
  name         = "fdinterestrates.csv"
  content_type = "csv"
  source       = "files/tables/fdinterestrates.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "fdinterestrates" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"REQUIRED\",\"name\":\"bucket_start_days\",\"type\":\"INTEGER\"},{\"mode\":\"REQUIRED\",\"name\":\"bucket_end_days\",\"type\":\"INTEGER\"},{\"mode\":\"REQUIRED\",\"name\":\"rate_of_interest\",\"type\":\"FLOAT\"},{\"mode\":\"REQUIRED\",\"name\":\"rate_of_interest_sr_citizen\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"latest_record_indicator\",\"type\":\"BOOLEAN\"}]"
  table_id   = "FdInterestRates"
}
resource "google_bigquery_job" "loading_data_to_fdinterestrates_table" {
  depends_on = [google_bigquery_table.fdinterestrates, google_storage_bucket_object.fdinterestrates]
  project    = var.project
  job_id     = "job-loading_data_to_fdinterestrates_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/fdinterestrates.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.fdinterestrates.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "mutualfund" {
  name         = "mutualfund.csv"
  content_type = "csv"
  source       = "files/tables/mutualfund.csv"
  bucket       = google_storage_bucket.bq_tables.id
}
resource "google_bigquery_table" "mutualfund" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"mutual_fund_id\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"risk_category\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"type_of_fund\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"size\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"one_month\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"six_month\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"one_year\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"three_year\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"five_year\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"all_time\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"NAV\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"min_sip_amount\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"fund_size\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"expense_ratio\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"exit_load\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"stamp_duty\",\"type\":\"FLOAT\"}]"
  table_id   = "MutualFund"
}
resource "google_bigquery_job" "loading_data_to_mutualfund_table" {
  depends_on = [google_bigquery_table.mutualfund, google_storage_bucket_object.mutualfund]
  project    = var.project
  job_id     = "job-loading_data_to_mutualfund_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/mutualfund.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.mutualfund.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_storage_bucket_object" "mutualfundaccountholding" {
  name         = "mutualfundaccountholding.csv"
  content_type = "csv"
  source       = "files/tables/mutualfundaccountholding.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "mutualfundaccountholding" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"account_no\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"Scheme_Name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Scheme_Code\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"AMC_Name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"AMC_Code\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Number_of_Units\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"Latest_NAV\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"one_month_return\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"six_month_return\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"TTM_Return\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"XIRR\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"Long_Term_Status\",\"type\":\"BOOLEAN\"},{\"name\":\"risk_category\",\"type\":\"INTEGER\"},{\"name\":\"amount_invested\",\"type\":\"FLOAT\"}]"
  table_id   = "MutualFundAccountHolding"
}
resource "google_bigquery_job" "loading_data_to_mutualfundaccountholding_table" {
  depends_on = [google_bigquery_table.mutualfundaccountholding, google_storage_bucket_object.mutualfundaccountholding]
  project    = var.project
  job_id     = "job-loading_data_to_mutualfundaccountholding_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/mutualfundaccountholding.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.mutualfundaccountholding.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}
resource "google_storage_bucket_object" "overdraft" {
  name         = "overdraft.csv"
  content_type = "csv"
  source       = "files/tables/overdraft.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "overdraft" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"REQUIRED\",\"name\":\"customer_id\",\"type\":\"INTEGER\"},{\"mode\":\"REQUIRED\",\"name\":\"amount\",\"type\":\"FLOAT\"},{\"mode\":\"REQUIRED\",\"name\":\"interest_rate\",\"type\":\"FLOAT\"},{\"mode\":\"REQUIRED\",\"name\":\"min_interest_rate\",\"type\":\"FLOAT\"},{\"mode\":\"REQUIRED\",\"name\":\"processing_fee\",\"type\":\"FLOAT\"},{\"mode\":\"REQUIRED\",\"name\":\"min_processing_fee\",\"type\":\"FLOAT\"}]"
  table_id   = "Overdraft"
}
resource "google_bigquery_job" "loading_data_to_overdraft_table" {
  depends_on = [google_bigquery_table.overdraft, google_storage_bucket_object.overdraft]
  project    = var.project
  job_id     = "job-loading_data_to_overdraft_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/overdraft.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.overdraft.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}
resource "google_storage_bucket_object" "producttable" {
  name         = "producttable.csv"
  content_type = "csv"
  source       = "files/tables/producttable.csv"
  bucket       = google_storage_bucket.bq_tables.id
}

resource "google_bigquery_table" "producttable" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"product_name\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"product\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Partner_Product\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"rate_of_interest\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"partner_description\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"webpage\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"product_code\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"Partner_Type\",\"type\":\"STRING\"}]"
  table_id   = "ProductTable"
}
resource "google_bigquery_job" "loading_data_to_producttable_table" {
  depends_on = [google_bigquery_table.producttable, google_storage_bucket_object.producttable]
  project    = var.project
  job_id     = "job-loading_data_to_producttable_table-${var.project}"
  labels = {
    "my_job" = "load"
  }
  load {
    source_uris = [
      "gs://${google_storage_bucket.bq_tables.name}/producttable.csv",
    ]
    destination_table {
      project_id = var.project
      dataset_id = google_bigquery_dataset.dummybankdataset.dataset_id
      table_id   = google_bigquery_table.producttable.table_id
    }
    skip_leading_rows     = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]
    write_disposition     = "WRITE_APPEND"
    # autodetect = true
  }
}

resource "google_bigquery_table" "standinginstructions" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"account_id\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"SI_Type\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"billing_company\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Bill_Generation_Date\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"Next_Payment_Date\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"fund_transfer_frequency\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"fund_transfer_amount\",\"type\":\"FLOAT\"},{\"mode\":\"NULLABLE\",\"name\":\"Last_Payment_Date\",\"type\":\"DATE\"}]"
  table_id   = "StandingInstructions"
}

resource "google_bigquery_table" "userloginlog" {
  dataset_id = "DummyBankDataset"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"ip_address\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"customer_id\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"datetime\",\"type\":\"DATETIME\"}]"
  table_id   = "userLoginLog"
}

resource "google_bigquery_table" "predicted_expenses" {
  dataset_id = "ExpensePrediction"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"ac_id\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"category\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"sub_category\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"date\",\"type\":\"TIMESTAMP\"},{\"mode\":\"NULLABLE\",\"name\":\"transaction_amount\",\"type\":\"FLOAT\"}]"
  table_id   = "predicted_expenses"
}

# table for training data for expense prediction
resource "google_bigquery_table" "training_data" {
  dataset_id = "ExpensePrediction"
  project    = var.project
  schema     = "[{\"mode\":\"NULLABLE\",\"name\":\"ac_id\",\"type\":\"INTEGER\"},{\"mode\":\"NULLABLE\",\"name\":\"month_year\",\"type\":\"DATE\"},{\"mode\":\"NULLABLE\",\"name\":\"sub_category\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"category\",\"type\":\"STRING\"},{\"mode\":\"NULLABLE\",\"name\":\"transaction_amount\",\"type\":\"INTEGER\"}]"
  table_id   = "training_data"
}

#################[end] BQ tables #########################################

