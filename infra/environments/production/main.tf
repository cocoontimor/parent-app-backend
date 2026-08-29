# ============================================
# Cocoon — production environment
# ============================================
# Thin caller: all composition lives in modules/backend-stack. Adding dev later
# is a sibling directory with the same shape and dev values.

module "stack" {
  source = "../../modules/backend-stack"

  project_id  = "decent-genius-503000-h2"
  region      = "asia-southeast1"
  environment = "production"

  artifact_repository = "cocoon-prod"
  image_tag           = "prod"

  cloudsql_connection_name = "decent-genius-503000-h2:asia-southeast1:cocoon-db"
  database_name            = "cocoon_db"
  database_user            = "cocoon_db_admin"

  gs_bucket_name = "cocoon-media"
  app_host       = "app.cocoontimor.org"

  whatsapp_phone_number_id = "1203615992845484"

  # Existing Secret Manager secrets (from the VM deployment), referenced only.
  secret_ids = {
    SECRET_KEY                    = "django-secret-key-prod"
    POSTGRES_DATABASE_PASSWORD    = "postgres-password-prod"
    WHATSAPP_ACCESS_TOKEN         = "whatsapp-access-token-prod"
    WHATSAPP_APP_SECRET           = "whatsapp-app-secret-prod"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN = "whatsapp-webhook-verify-token-prod"
  }

  cicd_sa_email = "cocoon-prod-cicd@decent-genius-503000-h2.iam.gserviceaccount.com"

  min_instances = 0
}

output "service_url" {
  value = module.stack.service_url
}

output "runtime_service_account" {
  value = module.stack.runtime_service_account
}

output "scheduler_service_account" {
  value = module.stack.scheduler_service_account
}

output "migrate_job" {
  value = module.stack.migrate_job
}
