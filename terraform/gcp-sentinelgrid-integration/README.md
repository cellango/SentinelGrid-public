# SentinelGrid GCP Integration - Terraform Module

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This Terraform module sets up the necessary GCP resources for SentinelGrid to monitor your GCP project with read-only access.

## Features

- **Service Account**: Creates a GCP service account for authentication
- **Service Account Key**: Generates JSON key file for authentication
- **IAM Bindings**: Assigns read-only roles:
  - Viewer (basic read access)
  - Security Reviewer (security resources)
  - Cloud Asset Viewer (asset inventory)
  - Logs Viewer (Cloud Logging)
  - Monitoring Viewer (monitoring data)
  - Security Center Admin Viewer (Security Command Center)
  - Compute Viewer (Compute Engine)
  - Storage Object Viewer (Cloud Storage)

## Requirements

- Terraform >= 1.0
- Google Provider >= 5.0
- GCP project with appropriate permissions
- Service account or user with permissions to:
  - Create service accounts
  - Create service account keys
  - Assign IAM roles at project level

## Authentication

Before running Terraform, authenticate with GCP:

```bash
# Using gcloud CLI
gcloud auth application-default login

# Or set environment variables
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
export GOOGLE_PROJECT="your-project-id"
```

## Usage

### Basic Setup

```hcl
provider "google" {
  project = "your-project-id"
  region  = "us-central1"
}

module "sentinelgrid_integration" {
  source = "github.com/sentinelgrid/terraform-google-sentinelgrid-integration"

  service_account_id         = "sentinelgrid-monitor"
  service_account_display_name = "SentinelGrid Monitoring"
  
  tags = {
    Environment = "production"
    ManagedBy   = "SentinelGrid"
  }
}

# Output the required values
output "project_id" {
  description = "Paste this into SentinelGrid UI"
  value       = module.sentinelgrid_integration.project_id
}

output "service_account_email" {
  description = "Paste this into SentinelGrid UI"
  value       = module.sentinelgrid_integration.service_account_email
}

output "service_account_key_json" {
  description = "Paste this JSON into SentinelGrid UI (save it securely!)"
  value       = module.sentinelgrid_integration.service_account_key_json
  sensitive   = true
}
```

### Custom Service Account ID

```hcl
module "sentinelgrid_integration" {
  source = "github.com/sentinelgrid/terraform-google-sentinelgrid-integration"

  service_account_id = "my-custom-sentinelgrid-sa"
}
```

## Required Values for SentinelGrid UI

After applying, you'll need these three values:

1. **Project ID** (`project_id` output)
2. **Service Account Email** (`service_account_email` output)
3. **Service Account JSON Key** (`service_account_key_json` output) - **Save this immediately, it won't be shown again!**

## Permissions

The Service Account has **read-only** permissions:

- **Viewer**: Read access to all resources
- **Security Reviewer**: Read security-related resources
- **Cloud Asset Viewer**: Read Cloud Asset Inventory
- **Logs Viewer**: Read Cloud Logging logs
- **Monitoring Viewer**: Read monitoring data
- **Security Center Admin Viewer**: Read Security Command Center findings
- **Compute Viewer**: Read Compute Engine resources
- **Storage Object Viewer**: Read Cloud Storage objects (for logs)

**No write, delete, or modify permissions are granted.**

## Security

- **Least Privilege**: Only read-only permissions
- **Service Account Key**: Generated securely, should be stored in Secret Manager or similar
- **Role Scoping**: Roles assigned at project level (can be scoped to folders if needed)

## Data Sources

SentinelGrid can access:

- **Cloud Audit Logs**: All project activity
- **Security Command Center**: Security findings and recommendations
- **Cloud Asset Inventory**: All GCP resources
- **Cloud Logging**: Application and infrastructure logs
- **Cloud Monitoring**: Metrics and alerts
- **Resource Inventory**: All GCP resources

## Examples

See the `examples/` directory for more usage examples.

## Troubleshooting

### Error: Insufficient permissions

Ensure you have:
- `Service Account Admin` role to create service accounts
- `Service Account Key Admin` role to create keys
- `Project IAM Admin` role to assign IAM roles

### Error: Service Account already exists

If the service account already exists, you can import it:
```bash
terraform import google_service_account.sentinelgrid projects/PROJECT_ID/serviceAccounts/SERVICE_ACCOUNT_EMAIL
```

### Error: Invalid service account ID

Service account IDs must:
- Be 6-30 characters
- Start with a lowercase letter
- Contain only lowercase letters, numbers, and hyphens

## Support

For issues or questions, contact SentinelGrid support or open an issue in the repository.

## License

This module is provided as-is by SentinelGrid.

