# Basic Example - Service Principal with Read-Only Roles

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "azuread" {
}

module "sentinelgrid_integration" {
  source = "../../"

  application_name = "SentinelGrid Monitoring"
  
  tags = {
    Environment = "production"
    Project     = "security-monitoring"
    ManagedBy   = "SentinelGrid"
  }
}

# Output the required values to paste into SentinelGrid UI
output "tenant_id" {
  description = "Azure AD Tenant ID - Paste this into SentinelGrid UI"
  value       = module.sentinelgrid_integration.tenant_id
}

output "application_id" {
  description = "Application (Client) ID - Paste this into SentinelGrid UI"
  value       = module.sentinelgrid_integration.application_id
}

output "client_secret" {
  description = "Client Secret - Paste this into SentinelGrid UI (save it securely!)"
  value       = module.sentinelgrid_integration.client_secret
  sensitive   = true
}

output "subscription_id" {
  description = "Azure Subscription ID"
  value       = module.sentinelgrid_integration.subscription_id
}

