# SentinelGrid Azure Integration - Outputs

output "application_id" {
  description = "Application (Client) ID of the Service Principal (REQUIRED - paste this into SentinelGrid UI)"
  value       = azuread_application.sentinelgrid.application_id
  sensitive   = false
}

output "service_principal_id" {
  description = "Object ID of the Service Principal"
  value       = azuread_service_principal.sentinelgrid.object_id
}

output "client_secret" {
  description = "Client Secret (password) for the Service Principal (REQUIRED - paste this into SentinelGrid UI)"
  value       = azuread_service_principal_password.sentinelgrid.value
  sensitive   = true
}

output "tenant_id" {
  description = "Azure AD Tenant ID (REQUIRED - paste this into SentinelGrid UI)"
  value       = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  description = "Azure Subscription ID"
  value       = data.azurerm_subscription.current.subscription_id
}

output "subscription_display_name" {
  description = "Display name of the Azure subscription"
  value       = data.azurerm_subscription.current.display_name
}

# Note: Client Secret is sensitive and should be stored securely
# Users should copy it immediately as it won't be shown again

