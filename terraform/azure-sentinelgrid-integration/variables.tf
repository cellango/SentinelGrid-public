# SentinelGrid Azure Integration - Variables

variable "application_name" {
  type        = string
  description = "Display name for the Azure AD application"
  default     = "SentinelGrid Monitoring"
}

variable "subscription_id" {
  type        = string
  description = "Azure subscription ID (defaults to current subscription)"
  default     = null
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "Optional: Log Analytics workspace ID for additional access"
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Additional tags to apply to resources"
  default     = {}
}

