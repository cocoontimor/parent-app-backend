# ============================================
# Cloud Run Service Module (Cocoon web)
# ============================================
# Mirrors equilux/eq-infra modules/cloud-run conventions: Cloud Run v2,
# request-based billing (cpu_idle), Cloud SQL Unix-socket mount, Secret Manager
# env injection, startup/liveness probes, and ignore_changes on the image so
# CI/CD owns deploys. File-secret mounting is omitted — Cocoon uses env secrets
# only.

resource "google_cloud_run_v2_service" "api" {
  name     = var.service_name
  location = var.region
  ingress  = var.ingress

  template {
    service_account = var.service_account

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      name  = var.service_name
      image = var.image

      ports {
        container_port = var.container_port
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        # Throttle CPU between requests (request-based billing).
        cpu_idle = true
      }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      # Secrets from Secret Manager injected as env vars ("secret-name:version").
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

      startup_probe {
        initial_delay_seconds = 20
        timeout_seconds       = 10
        period_seconds        = 10
        failure_threshold     = 6
        http_get {
          path = var.health_check_path
          port = var.container_port
          dynamic "http_headers" {
            for_each = var.health_check_host != null ? [1] : []
            content {
              name  = "Host"
              value = var.health_check_host
            }
          }
        }
      }

      liveness_probe {
        initial_delay_seconds = 30
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3
        http_get {
          path = var.health_check_path
          port = var.container_port
          dynamic "http_headers" {
            for_each = var.health_check_host != null ? [1] : []
            content {
              name  = "Host"
              value = var.health_check_host
            }
          }
        }
      }
    }

    max_instance_request_concurrency = var.concurrency
    timeout                          = "${var.timeout_seconds}s"

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

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    # CI/CD deploys new images; Terraform manages everything else.
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  count = var.allow_unauthenticated ? 1 : 0

  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
