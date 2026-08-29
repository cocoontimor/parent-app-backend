# ============================================
# Non-secret env config (production)
# ============================================
# Sensitive values live in secrets.tf / Secret Manager.

locals {
  service_name = "cocoon-backend-production"

  # Cloud SQL via Unix socket: HOST is the socket dir, PORT names the socket file.
  db_host = "/cloudsql/${var.cloudsql_connection_name}"

  base_env_vars = {
    DEBUG = "False"
    # ".run.app" is a Django leading-dot wildcard covering the Cloud Run URL;
    # probes send Host=app_host (see health_check_host) so they aren't rejected.
    ALLOWED_HOSTS             = "${var.app_host},.run.app"
    CSRF_TRUSTED_ORIGINS      = "https://${var.app_host}"
    APP_BASE_URL              = "https://${var.app_host}"
    POSTGRES_DATABASE_HOST    = local.db_host
    POSTGRES_DATABASE_PORT    = "5432"
    POSTGRES_DATABASE_NAME    = var.database_name
    POSTGRES_DATABASE_USER    = var.database_user
    POSTGRES_DATABASE_SSLMODE = "disable" # Unix socket; the proxy encrypts.
    GS_BUCKET_NAME            = var.gs_bucket_name
    GS_PROJECT_ID             = var.project_id
    GS_LOCATION               = var.gs_location
    WHATSAPP_PHONE_NUMBER_ID  = var.whatsapp_phone_number_id
  }
}
