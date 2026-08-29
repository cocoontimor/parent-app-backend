variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "name" {
  description = "Cloud Scheduler job name."
  type        = string
}

variable "job_name" {
  description = "Target Cloud Run Job name to execute."
  type        = string
}

variable "schedule" {
  description = "Cron schedule, e.g. \"0 * * * *\"."
  type        = string
}

variable "time_zone" {
  type    = string
  default = "Asia/Dili"
}

variable "scheduler_sa" {
  description = "Service account email whose OAuth token authenticates the :run call."
  type        = string
}

variable "retry_count" {
  type    = number
  default = 1
}
