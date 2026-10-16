# Basic Example - IAM Role Only

terraform {
  required_version = ">= 1.0"
}

module "sentinelgrid_integration" {
  source = "../../"

  # Required variables (get these from SentinelGrid UI)
  sentinelgrid_external_id      = "550e8400-e29b-41d4-a716-446655440000"
  sentinelgrid_aws_account_id   = "987654321098"

  # Optional: Customize role name
  role_name = "SentinelGridMonitorRole"

  # Optional: Add tags
  tags = {
    Environment = "production"
    Project     = "security-monitoring"
  }
}

# Output the role ARN to paste into SentinelGrid UI
output "role_arn" {
  description = "Paste this ARN into the SentinelGrid UI"
  value       = module.sentinelgrid_integration.sentinelgrid_monitor_role_arn
}

