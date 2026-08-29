# ============================================
# Cocoon Production — Cloud Run + Jobs + Scheduler
# ============================================

locals {
  environment = "production"
  image       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repository}/backend:prod"
}

# ---- Service accounts -------------------------------------------------------

resource "google_service_account" "runtime" {
  account_id   = "cocoon-run-production"
  display_name = "Cocoon Cloud Run + Jobs runtime"
}

resource "google_service_account" "scheduler" {
  account_id   = "cocoon-scheduler-production"
  display_name = "Cocoon Cloud Scheduler (triggers Jobs)"
}

# ---- Runtime SA permissions -------------------------------------------------

resource "google_project_iam_member" "runtime_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Media uploads (django-storages). Bucket-scoped; skipped if no bucket set.
resource "google_storage_bucket_iam_member" "runtime_media" {
  count  = var.gs_bucket_name != "" ? 1 : 0
  bucket = var.gs_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

# ---- CI deployer permissions ------------------------------------------------
# The GitHub Actions SA deploys the service/jobs (which run AS the runtime SA)
# and manages the scheduler (which runs AS the scheduler SA), so it needs
# actAs on both, plus run.admin to deploy.

resource "google_project_iam_member" "cicd_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${var.cicd_sa_email}"
}

resource "google_service_account_iam_member" "cicd_actas_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.cicd_sa_email}"
}

resource "google_service_account_iam_member" "cicd_actas_scheduler" {
  service_account_id = google_service_account.scheduler.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.cicd_sa_email}"
}

# ---- Web service ------------------------------------------------------------

module "cloud_run" {
  source = "../../modules/cloud-run"

  project_id   = var.project_id
  region       = var.region
  environment  = local.environment
  service_name = local.service_name

  image           = local.image
  service_account = google_service_account.runtime.email

  cpu           = "1000m"
  memory        = "512Mi"
  min_instances = var.min_instances
  max_instances = 10
  concurrency   = 6

  cloudsql_instances = [var.cloudsql_connection_name]
  health_check_path  = "/health/"
  health_check_host  = var.app_host

  env_vars = local.base_env_vars
  secrets  = local.cloud_run_secrets

  allow_unauthenticated = true
}

# ---- Jobs (same image, command overridden) ---------------------------------

module "job_migrate" {
  source = "../../modules/cloud-run-job"

  region             = var.region
  job_name           = "cocoon-migrate-production"
  image              = local.image
  service_account    = google_service_account.runtime.email
  args               = ["migrate", "--no-input"]
  cloudsql_instances = [var.cloudsql_connection_name]
  env_vars           = local.base_env_vars
  secrets            = local.cloud_run_secrets
}

module "job_daily_digest" {
  source = "../../modules/cloud-run-job"

  region             = var.region
  job_name           = "cocoon-daily-digest-production"
  image              = local.image
  service_account    = google_service_account.runtime.email
  args               = ["run_daily_digest"]
  cloudsql_instances = [var.cloudsql_connection_name]
  env_vars           = local.base_env_vars
  secrets            = local.cloud_run_secrets
}

module "job_release_lessons" {
  source = "../../modules/cloud-run-job"

  region             = var.region
  job_name           = "cocoon-release-lessons-production"
  image              = local.image
  service_account    = google_service_account.runtime.email
  args               = ["release_lessons"]
  cloudsql_instances = [var.cloudsql_connection_name]
  env_vars           = local.base_env_vars
  secrets            = local.cloud_run_secrets
}

# ---- Scheduler (the clock) --------------------------------------------------

module "schedule_daily_digest" {
  source = "../../modules/scheduler-job"

  project_id   = var.project_id
  region       = var.region
  name         = "cocoon-daily-digest-production"
  job_name     = module.job_daily_digest.name
  schedule     = "0 15 * * *" # 15:00 Dili
  time_zone    = "Asia/Dili"
  scheduler_sa = google_service_account.scheduler.email
}

module "schedule_release_lessons" {
  source = "../../modules/scheduler-job"

  project_id   = var.project_id
  region       = var.region
  name         = "cocoon-release-lessons-production"
  job_name     = module.job_release_lessons.name
  schedule     = "0 * * * *" # hourly; per-cohort send_hour gates delivery
  time_zone    = "Asia/Dili"
  scheduler_sa = google_service_account.scheduler.email
}
