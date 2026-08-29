variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "name" {
  description = "Prefix for LB resource names."
  type        = string
}

variable "domain" {
  description = "Domain for the Google-managed SSL cert (e.g. app.cocoontimor.org)."
  type        = string
}

variable "cloud_run_service" {
  description = "Name of the Cloud Run service to route to."
  type        = string
}

variable "security_policy" {
  description = "Cloud Armor security policy id to attach to the backend (null = none)."
  type        = string
  default     = null
}

variable "ssl_certificate" {
  description = "Self-link of the Cloudflare Origin SSL cert (created out-of-band via gcloud)."
  type        = string
}
