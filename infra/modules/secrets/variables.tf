variable "project_id" {
  type = string
}

variable "environment" {
  type = string
}

variable "secrets" {
  description = "Map of secret_id -> { accessor_members }. Values are set out-of-band via gcloud."
  type = map(object({
    accessor_members = list(string)
  }))
  default = {}
}

variable "labels" {
  type    = map(string)
  default = {}
}
