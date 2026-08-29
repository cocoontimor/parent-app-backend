# ============================================
# External HTTPS Load Balancer -> Cloud Run
# ============================================
# Global external Application LB fronting a Cloud Run service via a serverless
# NEG (tiggie/eq pattern). Google-managed TLS for var.domain, Cloud Armor host
# allowlist on the backend, and an HTTP->HTTPS redirect. Point the domain's DNS
# A record at the reserved static IP (output.ip_address).

resource "google_compute_global_address" "ip" {
  name    = "${var.name}-ip"
  project = var.project_id
}

resource "google_compute_region_network_endpoint_group" "neg" {
  name                  = "${var.name}-neg"
  project               = var.project_id
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = var.cloud_run_service
  }
}

resource "google_compute_backend_service" "backend" {
  name                  = "${var.name}-backend"
  project               = var.project_id
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTPS"
  security_policy       = var.security_policy

  backend {
    group = google_compute_region_network_endpoint_group.neg.id
  }
}

resource "google_compute_url_map" "https" {
  name            = "${var.name}-urlmap"
  project         = var.project_id
  default_service = google_compute_backend_service.backend.id
}

# --- TLS via Certificate Manager with DNS authorization ----------------------
# DNS-authorized so the managed cert validates via a DNS record (a CNAME you add
# in Cloudflare) rather than through the LB. This lets Cloudflare proxy (orange
# cloud) sit in front: Cloudflare terminates TLS for users, and this cert secures
# the Cloudflare -> LB origin leg (set Cloudflare SSL mode to Full (strict)).

resource "google_certificate_manager_dns_authorization" "auth" {
  name    = "${var.name}-dnsauth"
  project = var.project_id
  domain  = var.domain
}

resource "google_certificate_manager_certificate" "cert" {
  name    = "${var.name}-cert"
  project = var.project_id

  managed {
    domains            = [var.domain]
    dns_authorizations = [google_certificate_manager_dns_authorization.auth.id]
  }
}

resource "google_certificate_manager_certificate_map" "map" {
  name    = "${var.name}-certmap"
  project = var.project_id
}

resource "google_certificate_manager_certificate_map_entry" "entry" {
  name         = "${var.name}-certmap-entry"
  project      = var.project_id
  map          = google_certificate_manager_certificate_map.map.name
  certificates = [google_certificate_manager_certificate.cert.id]
  hostname     = var.domain
}

resource "google_compute_target_https_proxy" "https" {
  name            = "${var.name}-https"
  project         = var.project_id
  url_map         = google_compute_url_map.https.id
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.map.id}"
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "${var.name}-https-fr"
  project               = var.project_id
  target                = google_compute_target_https_proxy.https.id
  ip_address            = google_compute_global_address.ip.id
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

# ---- HTTP -> HTTPS redirect -------------------------------------------------

resource "google_compute_url_map" "redirect" {
  name    = "${var.name}-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http" {
  name    = "${var.name}-http"
  project = var.project_id
  url_map = google_compute_url_map.redirect.id
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "${var.name}-http-fr"
  project               = var.project_id
  target                = google_compute_target_http_proxy.http.id
  ip_address            = google_compute_global_address.ip.id
  port_range            = "80"
  load_balancing_scheme = "EXTERNAL_MANAGED"
}
