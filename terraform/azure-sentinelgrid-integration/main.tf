# SentinelGrid Azure Integration - Main Configuration
# This module creates the necessary Service Principal and role assignments for SentinelGrid to monitor your Azure subscription

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

# Get current subscription information
data "azurerm_subscription" "current" {}

# Get current client configuration
data "azurerm_client_config" "current" {}

# ============================================================================
# Service Principal for SentinelGrid Monitoring
# ============================================================================

# Application (App Registration)
resource "azuread_application" "sentinelgrid" {
  display_name = var.application_name
  description   = "SentinelGrid monitoring application for Azure subscription"

  # Optional: Set redirect URIs if needed for OAuth
  # web {
  #   redirect_uris = ["https://api.sentinelgrid.ai/auth/azure/callback"]
  # }

  tags = var.tags
}

# Service Principal
resource "azuread_service_principal" "sentinelgrid" {
  application_id               = azuread_application.sentinelgrid.application_id
  app_role_assignment_required = false
  description                  = "Service principal for SentinelGrid to monitor Azure subscription (read-only access)"

  tags = var.tags
}

# Service Principal Password (Client Secret)
resource "azuread_service_principal_password" "sentinelgrid" {
  service_principal_id = azuread_service_principal.sentinelgrid.id
  display_name         = "SentinelGrid Monitoring Secret"
  
  # Optional: Set expiration (default is 2 years)
  # end_date = timeadd(timestamp(), "730h") # 2 years
}

# ============================================================================
# Role Assignments (Read-Only Permissions)
# ============================================================================

# Reader role - Basic read access to all resources
resource "azurerm_role_assignment" "reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Reader"
  principal_id         = azuread_service_principal.sentinelgrid.object_id
}

# Security Reader role - Read security-related resources
resource "azurerm_role_assignment" "security_reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Security Reader"
  principal_id         = azuread_service_principal.sentinelgrid.object_id
}

# Log Analytics Reader - Read logs from Log Analytics workspaces
resource "azurerm_role_assignment" "log_analytics_reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Log Analytics Reader"
  principal_id         = azuread_service_principal.sentinelgrid.object_id
}

# Monitoring Reader - Read monitoring data
resource "azurerm_role_assignment" "monitoring_reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Monitoring Reader"
  principal_id         = azuread_service_principal.sentinelgrid.object_id
}

# ============================================================================
# Optional: Log Analytics Workspace Access (if workspace specified)
# ============================================================================

resource "azurerm_role_assignment" "log_analytics_workspace_reader" {
  count                = var.log_analytics_workspace_id != null ? 1 : 0
  scope                = var.log_analytics_workspace_id
  role_definition_name = "Log Analytics Reader"
  principal_id         = azuread_service_principal.sentinelgrid.object_id
}

# ============================================================================
# Optional: Microsoft Defender for Cloud Access
# ============================================================================

# Note: Microsoft Defender for Cloud access is typically managed at the subscription level
# The Security Reader role above should provide access to Defender findings

# ============================================================================
# Optional: Activity Log Access
# ============================================================================

# Activity Log access is provided by the Monitoring Reader role above
# No additional resources needed

