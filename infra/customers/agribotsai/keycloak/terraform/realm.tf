# AgribotsAI Keycloak Realm
resource "keycloak_realm" "agribotsai" {
  realm                = var.customer_name
  enabled              = true
  display_name         = var.customer_display_name
  display_name_html    = "<b>${var.customer_display_name}</b>"
  
  # Security settings
  ssl_required                  = "external"
  password_policy               = "length(8) and digits(1) and lowerCase(1) and upperCase(1) and notUsername"
  
  # Token settings
  access_token_lifespan                = "1h"
  access_token_lifespan_for_implicit_flow = "15m"
  sso_session_idle_timeout            = "30m"
  sso_session_max_lifespan            = "10h"
  offline_session_idle_timeout        = "2592000" # 30 days
  
  # Login settings
  login_with_email_allowed            = true
  duplicate_emails_allowed            = false
  remember_me                         = true
  verify_email                        = false # Set to true for production
  
  # Note: Brute force protection and internationalization 
  # are configured via separate resources or in Keycloak admin console
}

