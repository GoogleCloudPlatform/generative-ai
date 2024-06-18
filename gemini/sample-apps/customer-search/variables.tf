variable "project" {
  description = "Project ID of GCP project "
  type        = string
}
variable "user_email" {
  description = "Email of Owner/Editor of the GCP Project"
  type        = string
}
variable "region" {
  default     = "us-central1"
  type        = string
  description = "Region where all the resources will be deployed - note that all resources may not be deployable in all possible regions"
}
variable "maps_api_key" {
  description = "Google Maps API Key - https://developers.google.com/maps/documentation/embed/get-api-key#console"
  type        = string
}