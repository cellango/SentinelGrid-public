# SentinelGrid AWS Integration - Variables

variable "sentinelgrid_external_id" {
  type        = string
  description = "External ID provided by SentinelGrid for cross-account role assumption"
  sensitive   = true
}

variable "sentinelgrid_aws_account_id" {
  type        = string
  description = "SentinelGrid's AWS account ID"
  default     = "987654321098" # TODO: Update with actual SentinelGrid AWS account ID
}

variable "role_name" {
  type        = string
  description = "Name for the IAM role (default: SentinelGridMonitorRole)"
  default     = "SentinelGridMonitorRole"
}

# CloudTrail Configuration
variable "enable_cloudtrail" {
  type        = bool
  description = "Enable CloudTrail trail creation/configuration"
  default     = false
}

variable "cloudtrail_name" {
  type        = string
  description = "Name for the CloudTrail trail"
  default     = "sentinelgrid-trail"
}

variable "cloudtrail_s3_bucket_name" {
  type        = string
  description = "Existing S3 bucket name for CloudTrail logs (creates new bucket if not provided)"
  default     = null
}

variable "cloudtrail_s3_bucket_name_prefix" {
  type        = string
  description = "Prefix for CloudTrail S3 bucket name (if creating new bucket)"
  default     = "sentinelgrid-cloudtrail-logs"
}

variable "cloudtrail_s3_bucket_prefix" {
  type        = string
  description = "S3 prefix for CloudTrail logs"
  default     = "cloudtrail-logs"
}

# GuardDuty Configuration
variable "enable_guardduty" {
  type        = bool
  description = "Enable GuardDuty detector"
  default     = true
}

# AWS Config Configuration
variable "enable_config" {
  type        = bool
  description = "Enable AWS Config"
  default     = false
}

variable "config_s3_bucket_name" {
  type        = string
  description = "Existing S3 bucket name for Config (creates new bucket if not provided)"
  default     = null
}

variable "config_s3_bucket_name_prefix" {
  type        = string
  description = "Prefix for Config S3 bucket name (if creating new bucket)"
  default     = "sentinelgrid-config"
}

variable "config_s3_bucket_prefix" {
  type        = string
  description = "S3 prefix for Config data"
  default     = "config"
}

# Security Hub Configuration
variable "enable_security_hub" {
  type        = bool
  description = "Enable Security Hub"
  default     = false
}

# Org/StackSet guidance (module is single-account; wrap in StackSets for org use)
variable "org_mode" {
  type        = bool
  description = "Set true when deploying via StackSets/organizations wrapper (informational only in this module)."
  default     = false
}

# Additional log sources (optional)
variable "additional_log_group_arns" {
  type        = list(string)
  description = "Optional list of CloudWatch Log Group ARNs (e.g., VPC Flow Logs, ALB/WAF/Lambda, DB audit) to permit read access"
  default     = []
}

variable "additional_s3_log_bucket_arns" {
  type        = list(string)
  description = "Optional list of S3 bucket ARNs containing logs (e.g., CloudTrail/flow/db dumps) to permit read access"
  default     = []
}

# Helper log groups (we do NOT enable flow/db logs automatically; this just creates destinations)
variable "create_flow_logs_log_group" {
  type        = bool
  description = "If true, create a CloudWatch Log Group placeholder for VPC Flow Logs (you still need to enable flow logs to this destination)."
  default     = false
}

variable "flow_logs_log_group_name" {
  type        = string
  description = "Name for the Flow Logs log group when create_flow_logs_log_group is true."
  default     = "/sentinelgrid/flow-logs"
}

variable "flow_logs_log_group_retention_days" {
  type        = number
  description = "Retention (days) for the Flow Logs log group."
  default     = 90
}

variable "create_db_audit_log_group" {
  type        = bool
  description = "If true, create a CloudWatch Log Group placeholder for DB audit logs (e.g., RDS/Aurora). You still need to direct logs to it."
  default     = false
}

variable "db_audit_log_group_name" {
  type        = string
  description = "Name for the DB audit log group when create_db_audit_log_group is true."
  default     = "/sentinelgrid/db-audit"
}

variable "db_audit_log_group_retention_days" {
  type        = number
  description = "Retention (days) for the DB audit log group."
  default     = 90
}

# Tags
variable "tags" {
  type        = map(string)
  description = "Additional tags to apply to resources"
  default     = {}
}
