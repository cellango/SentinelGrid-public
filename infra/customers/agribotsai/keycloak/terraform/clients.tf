# AgribotsAI Web Client (Public - Frontend)
resource "keycloak_openid_client" "agribotsai_web" {
  realm_id                     = keycloak_realm.agribotsai.id
  client_id                    = "${var.customer_name}-web"
  name                         = "${var.customer_display_name} Web Client"
  enabled                      = true
  access_type                  = "PUBLIC"
  standard_flow_enabled        = true
  implicit_flow_enabled        = false
  direct_access_grants_enabled = true
  service_accounts_enabled     = false
  
  valid_redirect_uris = var.frontend_urls
  web_origins         = ["+"]
  
  # Token settings
  access_token_lifespan = "1h"
}

# AgribotsAI API Client (Confidential - Backend)
resource "keycloak_openid_client" "agribotsai_api" {
  realm_id                     = keycloak_realm.agribotsai.id
  client_id                    = "${var.customer_name}-api"
  name                         = "${var.customer_display_name} API Client"
  enabled                      = true
  access_type                  = "CONFIDENTIAL"
  standard_flow_enabled        = false
  implicit_flow_enabled        = false
  direct_access_grants_enabled = false
  service_accounts_enabled     = true
  
  # Client authentication
  client_secret = null # Auto-generated
  
  # Token settings
  access_token_lifespan = "1h"
}

# SentinelGrid IAM Agent Client (Service Account - Shared)
resource "keycloak_openid_client" "iam_agent" {
  realm_id                     = keycloak_realm.agribotsai.id
  client_id                    = "sentinelgrid-iam-agent"
  name                         = "SentinelGrid IAM Agent"
  enabled                      = true
  access_type                  = "CONFIDENTIAL"
  standard_flow_enabled        = false
  implicit_flow_enabled        = false
  direct_access_grants_enabled = false
  service_accounts_enabled     = true
  
  # Client authentication
  client_secret = null # Auto-generated
  
  # Token settings
  access_token_lifespan = "1h"
}

# Get client secret for IAM Agent (for output)
data "keycloak_openid_client" "iam_agent_data" {
  realm_id  = keycloak_realm.agribotsai.id
  client_id = keycloak_openid_client.iam_agent.client_id
}

