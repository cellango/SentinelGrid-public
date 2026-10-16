variable "keycloak_url" {
  description = "Keycloak server URL"
  type        = string
  default     = "http://keycloak:8080"
}

variable "keycloak_client_id" {
  description = "Keycloak admin client ID"
  type        = string
  default     = "admin-cli"
}

variable "keycloak_client_secret" {
  description = "Keycloak admin client secret (leave empty for admin-cli)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "keycloak_username" {
  description = "Keycloak admin username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "keycloak_password" {
  description = "Keycloak admin password"
  type        = string
  sensitive   = true
}

variable "keycloak_tls_insecure" {
  description = "Skip TLS verification (for development only)"
  type        = bool
  default     = true
}

variable "customer_name" {
  description = "Customer/tenant name"
  type        = string
  default     = "agribotsai"
}

variable "customer_display_name" {
  description = "Customer display name"
  type        = string
  default     = "AgribotsAI"
}

variable "frontend_urls" {
  description = "Frontend redirect URLs"
  type        = list(string)
  default     = [
    "http://localhost:3000/*",
    "https://app.agribotsai.com/*"
  ]
}

