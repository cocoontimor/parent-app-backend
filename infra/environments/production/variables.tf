# ============================================
# Production variables (Cocoon)
# ============================================

variable "project_id" {
  type    = string
  default = "decent-genius-503000-h2"
}

variable "region" {
  type    = string
  default = "asia-southeast1"
}

# Existing Artifact Registry repo the CI workflow already pushes to.
variable "artifact_repository" {
  type    = string
  default = "cocoon-prod"
}

# Cloud SQL instance connection name: "project:region:instance".
variable "cloudsql_connection_name" {
  type    = string
  default = "decent-genius-503000-h2:asia-southeast1:cocoon-db"
}

# Database (non-secret parts).
variable "database_name" {
  type    = string
  default = "cocoon_db"
}

variable "database_user" {
  type    = string
  default = "cocoon_db_admin"
}

# GCS media bucket (django-storages). Empty falls back to local FS (not for prod).
variable "gs_bucket_name" {
  type    = string
  default = "cocoon-media"
}

variable "gs_location" {
  type    = string
  default = "media"
}

# Public host(s) the app serves on. The .run.app URL is added automatically.
variable "app_host" {
  type    = string
  default = "app.cocoontimor.org"
}

variable "whatsapp_phone_number_id" {
  type    = string
  default = "1203615992845484" # Non-secret ID; token/app-secret live in Secret Manager.
}

# CI deployer service account (already used by the GitHub Actions workflow).
variable "cicd_sa_email" {
  type    = string
  default = "cocoon-prod-cicd@decent-genius-503000-h2.iam.gserviceaccount.com"
}

variable "min_instances" {
  type    = number
  default = 0
}
