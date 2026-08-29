output "url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.api.uri
}

output "name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.api.name
}

output "latest_revision" {
  description = "Latest revision name"
  value       = google_cloud_run_v2_service.api.latest_ready_revision
}
