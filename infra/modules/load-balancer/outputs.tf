output "ip_address" {
  description = "Static IP to point the domain's DNS A record at (Cloudflare proxied)."
  value       = google_compute_global_address.ip.address
}

output "dns_auth_record" {
  description = "Validation record for the managed cert: add this CNAME in Cloudflare (DNS-only)."
  value = {
    name = google_certificate_manager_dns_authorization.auth.dns_resource_record[0].name
    type = google_certificate_manager_dns_authorization.auth.dns_resource_record[0].type
    data = google_certificate_manager_dns_authorization.auth.dns_resource_record[0].data
  }
}
