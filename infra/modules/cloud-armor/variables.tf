variable "project_id" {
  type = string
}

variable "policy_name" {
  type = string
}

variable "allowed_hosts" {
  description = "Hostnames whose requests are allowed through; any other Host gets a 404."
  type        = list(string)
}

variable "description" {
  type    = string
  default = "Deny traffic not targeting a known hostname."
}
