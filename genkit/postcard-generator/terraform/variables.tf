variable "project_id" {
  type        = string
  description = "Deployment Project ID"
}

variable "firebase_app_hosting" {
  type        = bool
  description = "Configure App Hosting Service Account - only do this after it's been initialised via the CLI"
  default     = false
}
