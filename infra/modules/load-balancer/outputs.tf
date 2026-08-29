output "ip_address" {
  description = "Static IP to point the domain's DNS A record at."
  value       = google_compute_global_address.ip.address
}

output "cert_name" {
  value = google_compute_managed_ssl_certificate.cert.name
}
