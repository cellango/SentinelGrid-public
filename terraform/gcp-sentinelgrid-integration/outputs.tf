# SentinelGrid GCP Integration - Outputs

output "project_id" {
  description = "GCP Project ID (REQUIRED - paste this into SentinelGrid UI)"
  value       = data.google_project.current.project_id
}

output "service_account_email" {
  description = "Service Account email (REQUIRED - paste this into SentinelGrid UI)"
  value       = google_service_account.sentinelgrid.email
}

output "service_account_key_json" {
  description = "Service Account JSON key (REQUIRED - paste this into SentinelGrid UI, save it securely!)"
  value       = local.service_account_key_json
  sensitive   = true
}

output "service_account_id" {
  description = "Service Account ID"
  value       = google_service_account.sentinelgrid.account_id
}

output "service_account_name" {
  description = "Service Account full name"
  value       = google_service_account.sentinelgrid.name
}

# Note: Service Account JSON key is sensitive and should be stored securely
# Users should copy it immediately as it won't be shown again

