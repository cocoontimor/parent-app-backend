# ============================================
# backend-stack — Cloud Run + Jobs + Scheduler for one environment
# ============================================

locals {
  service_name = "cocoon-backend-${var.environment}"
  image        = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repository}/backend:${var.image_tag}"

  # Cloud SQL via Unix socket: HOST is the socket dir, PORT names the socket file.
  db_host = "/cloudsql/${var.cloudsql_connection_name}"

  base_env_vars = {
    DEBUG = "False"
    # ".run.app" is a Django leading-dot wildcard covering the Cloud Run URL;
    # probes send Host=app_host (see health_check_host) so they aren't rejected.
    ALLOWED_HOSTS             = "${var.app_host},.run.app"
    CSRF_TRUSTED_ORIGINS      = "https://${var.app_host}"
    APP_BASE_URL              = "https://${var.app_host}"
    POSTGRES_DATABASE_HOST    = local.db_host
    POSTGRES_DATABASE_PORT    = "5432"
    POSTGRES_DATABASE_NAME    = var.database_name
    POSTGRES_DATABASE_USER    = var.database_user
    POSTGRES_DATABASE_SSLMODE = "disable" # Unix socket; the proxy encrypts.
    GS_BUCKET_NAME            = var.gs_bucket_name
    GS_PROJECT_ID             = var.project_id
    GS_LOCATION               = var.gs_location
    WHATSAPP_PHONE_NUMBER_ID  = var.whatsapp_phone_number_id
  }

  cloud_run_secrets = { for k, v in var.secret_ids : k => "${v}:latest" }
  runtime_sa_member = "serviceAccount:${google_service_account.runtime.email}"
}

# ---- Service accounts -------------------------------------------------------

resource "google_service_account" "runtime" {
  account_id   = "cocoon-run-${var.environment}"
  display_name = "Cocoon Cloud Run + Jobs runtime (${var.environment})"
}

resource "google_service_account" "scheduler" {
  account_id   = "cocoon-sched-${var.environment}"
  display_name = "Cocoon Cloud Scheduler (${var.environment})"
}

# ---- Runtime SA permissions -------------------------------------------------

resource "google_project_iam_member" "runtime_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = local.runtime_sa_member
}

resource "google_storage_bucket_iam_member" "runtime_media" {
  count  = var.gs_bucket_name != "" ? 1 : 0
  bucket = var.gs_bucket_name
  role   = "roles/storage.objectAdmin"
  member = local.runtime_sa_member
}

# Media is served via signed URLs (querystring_auth). The runtime SA signs with
# the IAM signBlob API because its metadata-server credentials have no private
# key; that requires the SA to be able to create tokens for itself.
resource "google_service_account_iam_member" "runtime_sign_blob" {
  count              = var.gs_bucket_name != "" ? 1 : 0
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = local.runtime_sa_member
}

# Grant the runtime SA read access to each existing secret.
resource "google_secret_manager_secret_iam_member" "runtime_accessors" {
  for_each = var.secret_ids

  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = local.runtime_sa_member
}

# ---- CI deployer permissions ------------------------------------------------

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
  source = "../cloud-run"

  project_id   = var.project_id
  region       = var.region
  environment  = var.environment
  service_name = local.service_name

  image           = local.image
  service_account = google_service_account.runtime.email
  ingress         = var.ingress

  cpu           = var.cpu
  memory        = var.memory
  min_instances = var.min_instances
  max_instances = var.max_instances
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
  source = "../cloud-run-job"

  region             = var.region
  job_name           = "cocoon-migrate-${var.environment}"
  image              = local.image
  service_account    = google_service_account.runtime.email
  args               = ["migrate", "--no-input"]
  cloudsql_instances = [var.cloudsql_connection_name]
  env_vars           = local.base_env_vars
  secrets            = local.cloud_run_secrets
}

module "job_daily_digest" {
  source = "../cloud-run-job"

  region             = var.region
  job_name           = "cocoon-daily-digest-${var.environment}"
  image              = local.image
  service_account    = google_service_account.runtime.email
  args               = ["run_daily_digest"]
  cloudsql_instances = [var.cloudsql_connection_name]
  env_vars           = local.base_env_vars
  secrets            = local.cloud_run_secrets
}

module "job_release_lessons" {
  source = "../cloud-run-job"

  region             = var.region
  job_name           = "cocoon-release-lessons-${var.environment}"
  image              = local.image
  service_account    = google_service_account.runtime.email
  args               = ["release_lessons"]
  cloudsql_instances = [var.cloudsql_connection_name]
  env_vars           = local.base_env_vars
  secrets            = local.cloud_run_secrets
}

# ---- Scheduler (the clock) --------------------------------------------------

module "schedule_daily_digest" {
  source = "../scheduler-job"

  project_id   = var.project_id
  region       = var.region
  name         = "cocoon-daily-digest-${var.environment}"
  job_name     = module.job_daily_digest.name
  schedule     = var.digest_schedule
  time_zone    = var.schedule_time_zone
  scheduler_sa = google_service_account.scheduler.email
}

module "schedule_release_lessons" {
  source = "../scheduler-job"

  project_id   = var.project_id
  region       = var.region
  name         = "cocoon-release-lessons-${var.environment}"
  job_name     = module.job_release_lessons.name
  schedule     = var.lessons_schedule
  time_zone    = var.schedule_time_zone
  scheduler_sa = google_service_account.scheduler.email
}
