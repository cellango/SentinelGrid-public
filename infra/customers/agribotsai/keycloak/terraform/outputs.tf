output "realm_id" {
  description = "Keycloak realm ID"
  value       = keycloak_realm.agribotsai.id
}

output "realm_name" {
  description = "Keycloak realm name"
  value       = keycloak_realm.agribotsai.realm
}

output "web_client_id" {
  description = "Web client ID"
  value       = keycloak_openid_client.agribotsai_web.client_id
}

output "api_client_id" {
  description = "API client ID"
  value       = keycloak_openid_client.agribotsai_api.client_id
}

output "iam_agent_client_id" {
  description = "IAM Agent client ID"
  value       = keycloak_openid_client.iam_agent.client_id
}

output "iam_agent_client_secret" {
  description = "IAM Agent client secret"
  value       = data.keycloak_openid_client.iam_agent_data.client_secret
  sensitive   = true
}

output "admin_user_id" {
  description = "Admin user ID"
  value       = keycloak_user.admin.id
}

output "admin_username" {
  description = "Admin username"
  value       = keycloak_user.admin.username
}

output "token_endpoint" {
  description = "Keycloak token endpoint URL"
  value       = "${var.keycloak_url}/realms/${keycloak_realm.agribotsai.realm}/protocol/openid-connect/token"
}

