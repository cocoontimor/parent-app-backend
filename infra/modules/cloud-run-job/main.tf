# ============================================
# Cloud Run Job Module (Cocoon batch/scheduled work)
# ============================================
# Same image as the web service; the container command is overridden with a
# management command (e.g. `python manage.py release_lessons`). Used for the
# migrate job and the Cloud Scheduler-triggered task jobs. No public surface —
# execution is IAM-gated.

resource "google_cloud_run_v2_job" "job" {
  name     = var.job_name
  location = var.region

  template {
    template {
      service_account = var.service_account
      timeout         = "${var.timeout_seconds}s"
      max_retries     = var.max_retries

      containers {
        image   = var.image
        command = var.command
        args    = var.args

        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = var.secrets
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = split(":", env.value)[0]
                version = split(":", env.value)[1]
              }
            }
          }
        }

        dynamic "volume_mounts" {
          for_each = length(var.cloudsql_instances) > 0 ? [1] : []
          content {
            name       = "cloudsql"
            mount_path = "/cloudsql"
          }
        }

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }
      }

      dynamic "volumes" {
        for_each = length(var.cloudsql_instances) > 0 ? [1] : []
        content {
          name = "cloudsql"
          cloud_sql_instance {
            instances = var.cloudsql_instances
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
      client,
      client_version,
    ]
  }
}
