# ============================================
# Cloud Scheduler -> Cloud Run Job trigger
# ============================================
# Fires on a cron schedule and POSTs to the Cloud Run Admin API to execute a
# job. Auth is an OAuth token minted for var.scheduler_sa (Google APIs need
# OAuth, not OIDC). The SA is granted run.invoker on the job so it can execute
# it (run.jobs.run).

resource "google_cloud_scheduler_job" "trigger" {
  name      = var.name
  project   = var.project_id
  region    = var.region
  schedule  = var.schedule
  time_zone = var.time_zone

  attempt_deadline = "320s"

  retry_config {
    retry_count = var.retry_count
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.job_name}:run"

    oauth_token {
      service_account_email = var.scheduler_sa
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }
}

# Let the scheduler SA execute this specific job.
resource "google_cloud_run_v2_job_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  name     = var.job_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.scheduler_sa}"
}
