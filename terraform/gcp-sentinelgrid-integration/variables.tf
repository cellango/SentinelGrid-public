# SentinelGrid GCP Integration - Variables

variable "service_account_id" {
  type        = string
  description = "ID for the service account (must be unique within the project)"
  default     = "sentinelgrid-monitor"
  
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,61}[a-z0-9]$", var.service_account_id))
    error_message = "Service account ID must be 6-30 characters, start with lowercase letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "service_account_display_name" {
  type        = string
  description = "Display name for the service account"
  default     = "SentinelGrid Monitoring"
}

variable "project_id" {
  type        = string
  description = "GCP project ID (defaults to current project)"
  default     = null
}

variable "create_service_account_key" {
  type        = bool
  description = "Whether to create a service account key (JSON key file)"
  default     = true
}

variable "tags" {
  type        = map(string)
  description = "Additional labels/tags to apply to resources"
  default     = {}
}

