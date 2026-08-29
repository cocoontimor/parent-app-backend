# ============================================
# backend-stack — full Cocoon environment (web + jobs + scheduler)
# ============================================
# One call = one environment. `environment` drives all resource names, so dev
# and production never collide even in the same project.

variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "asia-southeast1"
}

variable "environment" {
  description = "Environment name; drives resource names (e.g. \"production\", \"dev\")."
  type        = string
}

variable "artifact_repository" {
  type = string
}

variable "image_tag" {
  description = "Image tag CI deploys to for this env (e.g. \"prod\", \"dev\")."
  type        = string
}

variable "cloudsql_connection_name" {
  type = string
}

variable "database_name" {
  type = string
}

variable "database_user" {
  type = string
}

variable "gs_bucket_name" {
  type    = string
  default = ""
}

variable "gs_location" {
  type    = string
  default = "media"
}

variable "app_host" {
  description = "Public host the app serves on. \".run.app\" is always also allowed."
  type        = string
}

variable "whatsapp_phone_number_id" {
  type    = string
  default = ""
}

variable "secret_ids" {
  description = "env-var name -> existing Secret Manager secret id (referenced, not created)."
  type        = map(string)
}

variable "cicd_sa_email" {
  description = "CI deployer SA; granted actAs on the runtime/scheduler SAs + run.admin."
  type        = string
}

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 10
}

variable "cpu" {
  type    = string
  default = "1000m"
}

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "digest_schedule" {
  type    = string
  default = "0 15 * * *" # 15:00 Dili
}

variable "lessons_schedule" {
  type    = string
  default = "0 * * * *" # hourly; per-cohort send_hour gates delivery
}

variable "schedule_time_zone" {
  type    = string
  default = "Asia/Dili"
}
