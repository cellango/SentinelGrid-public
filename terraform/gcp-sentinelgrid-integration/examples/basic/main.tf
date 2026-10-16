# Basic Example - Service Account with Read-Only Roles

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "your-project-id"  # Replace with your GCP project ID
  region  = "us-central1"
}

module "sentinelgrid_integration" {
  source = "../../"

  service_account_id           = "sentinelgrid-monitor"
  service_account_display_name = "SentinelGrid Monitoring"
  
  tags = {
    Environment = "production"
    Project     = "security-monitoring"
    ManagedBy   = "SentinelGrid"
  }
}

# Output the required values to paste into SentinelGrid UI
output "project_id" {
  description = "GCP Project ID - Paste this into SentinelGrid UI"
  value       = module.sentinelgrid_integration.project_id
}

output "service_account_email" {
  description = "Service Account Email - Paste this into SentinelGrid UI"
  value       = module.sentinelgrid_integration.service_account_email
}

output "service_account_key_json" {
  description = "Service Account JSON Key - Paste this into SentinelGrid UI (save it securely!)"
  value       = module.sentinelgrid_integration.service_account_key_json
  sensitive   = true
}

