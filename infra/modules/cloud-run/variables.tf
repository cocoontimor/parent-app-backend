variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "environment" {
  type = string
}

variable "service_name" {
  type = string
}

variable "image" {
  type = string
}

variable "cpu" {
  type    = string
  default = "1000m"
}

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 10
}

variable "concurrency" {
  # gunicorn --workers=3 --threads=2 = 6 real concurrent slots per instance.
  type    = number
  default = 6
}

variable "timeout_seconds" {
  type    = number
  default = 300
}

variable "cloudsql_instances" {
  description = "Cloud SQL connection names to attach (mounts a Unix socket at /cloudsql/<conn>)."
  type        = list(string)
  default     = []
}

variable "container_port" {
  description = "Container port the app listens on (Cloud Run injects this as $PORT)."
  type        = number
  default     = 8080
}

variable "health_check_path" {
  type    = string
  default = "/health/"
}

variable "health_check_host" {
  description = "Host header on probes so ALLOWED_HOSTS enforcement doesn't 400 them. null = no override."
  type        = string
  default     = null
}

variable "ingress" {
  type    = string
  default = "INGRESS_TRAFFIC_ALL"
}

variable "service_account" {
  type    = string
  default = null
}

variable "env_vars" {
  type    = map(string)
  default = {}
}

variable "secrets" {
  description = "Env-var name -> \"secret-name:version\" for Secret Manager entries injected as env vars."
  type        = map(string)
  default     = {}
}

variable "allow_unauthenticated" {
  type    = bool
  default = false
}
