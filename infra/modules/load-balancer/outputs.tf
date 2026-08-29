output "ip_address" {
  description = "Static IP to point the domain's DNS A record at (Cloudflare proxied)."
  value       = google_compute_global_address.ip.address
}
