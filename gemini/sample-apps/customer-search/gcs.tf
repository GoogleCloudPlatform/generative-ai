
resource "google_storage_bucket" "document_bucket_vertexai" {
  force_destroy               = false
  location                    = "US-CENTRAL1"
  name                        = "${var.project}_document_bucket_vertexai"
  project                     = var.project
  public_access_prevention    = "inherited"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "neo_bank_faq_documents" {
  force_destroy               = false
  location                    = "ASIA-SOUTH1"
  name                        = "${var.project}_neo-bank-faq-documents"
  project                     = var.project
  public_access_prevention    = "enforced"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "upload_bucket9" {
  force_destroy               = false
  location                    = "US"
  name                        = "${var.project}_upload_bucket9"
  project                     = var.project
  public_access_prevention    = "enforced"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
}

