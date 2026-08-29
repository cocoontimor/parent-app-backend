output "service_url" {
  value = module.cloud_run.url
}

output "runtime_service_account" {
  value = google_service_account.runtime.email
}

output "scheduler_service_account" {
  value = google_service_account.scheduler.email
}

output "migrate_job" {
  value = module.job_migrate.name
}
