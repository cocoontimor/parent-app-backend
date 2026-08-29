# ============================================
# Secret Manager wiring (production)
# ============================================
# Secret VALUES are created out-of-band (see infra/README.md). Terraform manages
# the secret resources + grants the runtime SA access.

locals {
  env_suffix = "production"

  # env-var name -> secret-manager secret id
  secret_env = {
    SECRET_KEY                    = "cocoon-secret-key-${local.env_suffix}"
    POSTGRES_DATABASE_PASSWORD    = "cocoon-postgres-database-password-${local.env_suffix}"
    WHATSAPP_ACCESS_TOKEN         = "cocoon-whatsapp-access-token-${local.env_suffix}"
    WHATSAPP_APP_SECRET           = "cocoon-whatsapp-app-secret-${local.env_suffix}"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN = "cocoon-whatsapp-webhook-verify-token-${local.env_suffix}"
  }

  # Injected into Cloud Run / Jobs as "secret-id:latest".
  cloud_run_secrets = { for k, v in local.secret_env : k => "${v}:latest" }

  runtime_sa_member = "serviceAccount:${google_service_account.runtime.email}"
}

module "secrets" {
  source = "../../modules/secrets"

  project_id  = var.project_id
  environment = local.environment

  secrets = {
    for k, secret_id in local.secret_env :
    secret_id => { accessor_members = [local.runtime_sa_member] }
  }
}
