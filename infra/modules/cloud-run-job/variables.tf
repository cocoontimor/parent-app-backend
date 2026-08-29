variable "region" {
  type = string
}

variable "job_name" {
  type = string
}

variable "image" {
  type = string
}

variable "service_account" {
  type    = string
  default = null
}

variable "command" {
  description = "Container entrypoint override, e.g. [\"python\", \"manage.py\"]."
  type        = list(string)
  default     = ["python", "manage.py"]
}

variable "args" {
  description = "Args appended to command, e.g. [\"release_lessons\"]."
  type        = list(string)
}

variable "cpu" {
  type    = string
  default = "1000m"
}

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "timeout_seconds" {
  type    = number
  default = 900
}

variable "max_retries" {
  type    = number
  default = 1
}

variable "cloudsql_instances" {
  type    = list(string)
  default = []
}

variable "env_vars" {
  type    = map(string)
  default = {}
}

variable "secrets" {
  type    = map(string)
  default = {}
}
