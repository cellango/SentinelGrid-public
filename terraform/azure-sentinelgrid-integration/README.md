# SentinelGrid Azure Integration - Terraform Module

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This Terraform module sets up the necessary Azure resources for SentinelGrid to monitor your Azure subscription with read-only access.

## Features

- **Service Principal**: Creates Azure AD application and service principal
- **Client Secret**: Generates authentication secret
- **Role Assignments**: Assigns read-only roles:
  - Reader (basic read access)
  - Security Reader (security resources)
  - Log Analytics Reader (log access)
  - Monitoring Reader (monitoring data)

## Requirements

- Terraform >= 1.0
- Azure Provider >= 3.0
- Azure AD Provider >= 2.0
- Azure subscription with appropriate permissions
- Azure CLI or service principal with permissions to:
  - Create Azure AD applications
  - Assign roles at subscription level

## Authentication

Before running Terraform, authenticate with Azure:

```bash
# Using Azure CLI
az login

# Or set environment variables
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"
export ARM_SUBSCRIPTION_ID="your-subscription-id"
export ARM_TENANT_ID="your-tenant-id"
```

## Usage

### Basic Setup

```hcl
provider "azurerm" {
  features {}
}

provider "azuread" {
}

module "sentinelgrid_integration" {
  source = "github.com/sentinelgrid/terraform-azurerm-sentinelgrid-integration"

  application_name = "SentinelGrid Monitoring"
  
  tags = {
    Environment = "production"
    ManagedBy   = "SentinelGrid"
  }
}

# Output the required values
output "application_id" {
  description = "Paste this into SentinelGrid UI"
  value       = module.sentinelgrid_integration.application_id
}

output "client_secret" {
  description = "Paste this into SentinelGrid UI (save it securely!)"
  value       = module.sentinelgrid_integration.client_secret
  sensitive   = true
}

output "tenant_id" {
  description = "Paste this into SentinelGrid UI"
  value       = module.sentinelgrid_integration.tenant_id
}
```

### With Log Analytics Workspace

```hcl
module "sentinelgrid_integration" {
  source = "github.com/sentinelgrid/terraform-azurerm-sentinelgrid-integration"

  application_name              = "SentinelGrid Monitoring"
  log_analytics_workspace_id    = "/subscriptions/.../resourceGroups/.../providers/Microsoft.OperationalInsights/workspaces/my-workspace"
  
  tags = {
    Environment = "production"
  }
}
```

## Required Values for SentinelGrid UI

After applying, you'll need these three values:

1. **Tenant ID** (`tenant_id` output)
2. **Application (Client) ID** (`application_id` output)
3. **Client Secret** (`client_secret` output) - **Save this immediately, it won't be shown again!**

## Permissions

The Service Principal has **read-only** permissions:

- **Reader**: Read access to all resources
- **Security Reader**: Read security-related resources (Microsoft Defender for Cloud, Security Center)
- **Log Analytics Reader**: Read logs from Log Analytics workspaces
- **Monitoring Reader**: Read monitoring data (Activity Log, metrics)

**No write, delete, or modify permissions are granted.**

## Security

- **Least Privilege**: Only read-only permissions
- **Client Secret**: Generated securely, should be stored in Azure Key Vault or similar
- **Role Scoping**: Roles assigned at subscription level (can be scoped to resource groups if needed)

## Data Sources

SentinelGrid can access:

- **Activity Log**: All subscription activity
- **Microsoft Defender for Cloud**: Security findings and recommendations
- **Azure Policy**: Compliance status
- **Log Analytics**: Application and infrastructure logs
- **Resource Inventory**: All Azure resources

## Examples

See the `examples/` directory for more usage examples.

## Troubleshooting

### Error: Insufficient permissions

Ensure you have:
- `Application Administrator` or `Global Administrator` role in Azure AD
- `Owner` or `User Access Administrator` role at subscription level

### Error: Service Principal already exists

If the application already exists, you can import it:
```bash
terraform import azuread_application.sentinelgrid <application-id>
```

## Support

For issues or questions, contact SentinelGrid support or open an issue in the repository.

## License

This module is provided as-is by SentinelGrid.

