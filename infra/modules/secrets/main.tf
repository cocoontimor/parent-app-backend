# ============================================
# Secret Manager Module
# ============================================
# Creates secrets + grants secretAccessor. Secret VALUES are set out-of-band via
# gcloud (never in Terraform state) — `value` stays null here.

resource "google_secret_manager_secret" "main" {
  for_each = var.secrets

  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  labels = merge(var.labels, {
    environment = var.environment
    managed_by  = "terraform"
  })
}

# Grant accessor role to specified service-account members.
resource "google_secret_manager_secret_iam_member" "accessors" {
  for_each = { for item in local.accessor_bindings : "${item.secret}-${item.member}" => item }

  project   = var.project_id
  secret_id = google_secret_manager_secret.main[each.value.secret].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = each.value.member
}

locals {
  accessor_bindings = flatten([
    for secret_key, secret_config in var.secrets : [
      for member in secret_config.accessor_members : {
        secret = secret_key
        member = member
      }
    ]
  ])
}
