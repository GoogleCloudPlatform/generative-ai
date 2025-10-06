output "maps_public_api_key" {
  description = "Maps API key for local development"
  value       = google_secret_manager_secret_version.maps_public.secret_data
  sensitive   = true
}

output "maps_server_api_key" {
  description = "Maps API key for local development"
  value       = google_secret_manager_secret_version.maps_server.secret_data
  sensitive   = true
}
