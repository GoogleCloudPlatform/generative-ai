# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

locals {
  concierge_vpc_name         = "concierge-vpc"
  concierge_subnet_name      = "concierge-subnet"
  concierge_vpc_peering_name = "concierge-vpc-peering"
}

# Create a VPC network and a single subnet for the concierge demo.
module "vpc" {
  source  = "terraform-google-modules/network/google"
  version = "~> 10.0"

  project_id   = module.project-factory.project_id
  network_name = local.concierge_vpc_name
  routing_mode = "GLOBAL"

  subnets = [
    {
      subnet_name   = local.concierge_subnet_name
      subnet_ip     = "10.10.10.0/24"
      subnet_region = var.region
    }
  ]
  depends_on = [module.project-factory]
}

# Create an IP address for the VPC peering connection.
resource "google_compute_global_address" "google_services_ip_alloc" {
  project       = module.project-factory.project_id
  name          = local.concierge_vpc_peering_name
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = module.vpc.network_id
}

# Create a private service networking connection.
resource "google_service_networking_connection" "google_services_connection" {
  network                 = module.vpc.network_id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.google_services_ip_alloc.name]
}
