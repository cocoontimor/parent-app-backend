#!/bin/bash
set -euo pipefail

# ============================================
# cloud-sql-proxy → cocoon-db (production)
# --------------------------------------------
# Opens a local TCP tunnel to the Cloud SQL
# instance, authenticating as the developer's
# own gcloud ADC identity (roles/owner covers
# cloudsql.client).
#
# Prereqs (one-time):
#   1. brew install cloud-sql-proxy
#   2. gcloud auth application-default login
# ============================================

PROJECT_ID="decent-genius-503000-h2"
INSTANCE_CONNECTION_NAME="decent-genius-503000-h2:asia-southeast1:cocoon-db"
DB_NAME="cocoon_db"
DB_USER="cocoon_db_admin"
PASSWORD_SECRET="postgres-password-prod"
LOCAL_PORT="${LOCAL_PORT:-5440}"

if ! command -v cloud-sql-proxy >/dev/null 2>&1; then
    echo "cloud-sql-proxy not installed. Install with:"
    echo "  brew install cloud-sql-proxy"
    exit 1
fi

cat <<EOF
Starting cloud-sql-proxy
  Instance : ${INSTANCE_CONNECTION_NAME}
  Bind     : 127.0.0.1:${LOCAL_PORT}
  Auth     : ADC (gcloud application-default)

Connect in another terminal with:
  PGPASSWORD=\$(gcloud secrets versions access latest \\
      --project=${PROJECT_ID} --secret=${PASSWORD_SECRET}) \\
    psql "host=127.0.0.1 port=${LOCAL_PORT} dbname=${DB_NAME} user=${DB_USER}"

Ctrl-C to stop.

EOF

exec cloud-sql-proxy \
    --port="${LOCAL_PORT}" \
    "${INSTANCE_CONNECTION_NAME}"
