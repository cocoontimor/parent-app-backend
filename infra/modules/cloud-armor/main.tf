# ============================================
# Cloud Armor Module (host allowlist)
# ============================================
# Ported from equilux/eq-infra. Requests whose Host header matches an allowed
# host pass; everything else (incl. raw LB-IP scans) gets a 404 at the edge,
# before reaching Cloud Run.

locals {
  hosts_alternation = join("|", [for h in var.allowed_hosts : replace(h, ".", "[.]")])
  host_match_regex  = "^(?:${local.hosts_alternation})(?::[0-9]+)?$"
}

resource "google_compute_security_policy" "policy" {
  name        = var.policy_name
  project     = var.project_id
  description = var.description

  rule {
    action      = "allow"
    priority    = 1000
    description = "Allow known hostnames"
    match {
      expr {
        expression = "request.headers['host'].lower().matches('${local.host_match_regex}')"
      }
    }
  }

  rule {
    action      = "deny(404)"
    priority    = 2147483647
    description = "Default deny for unknown hosts (incl. raw-IP scans)"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }
}
