terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.management_region
}

variable "management_region" {
  type        = string
  description = "Region to operate the StackSet/management actions"
  default     = "us-east-1"
}

variable "target_ou_ids" {
  type        = list(string)
  description = "List of OU IDs to target (e.g., ['ou-abcd-1234'])"
  default     = []
}

variable "target_account_ids" {
  type        = list(string)
  description = "Explicit account IDs if not using OUs"
  default     = []
}

variable "regions" {
  type        = list(string)
  description = "Regions to deploy the integration stack"
  default     = ["us-east-1", "us-west-2"]
}

variable "sentinelgrid_external_id" {
  type        = string
  description = "External ID provided by SentinelGrid"
}

variable "sentinelgrid_aws_account_id" {
  type        = string
  description = "SentinelGrid AWS account ID"
}

# NOTE: This example is a guidance wrapper. In practice, use aws_cloudformation_stack_set
# to deploy the module (or an embedded template) across OUs/accounts.
# For brevity, we illustrate a pseudo-call to the module per account/region.

locals {
  targets = length(var.target_account_ids) > 0 ? var.target_account_ids : var.target_ou_ids
}

module "sentinelgrid_integration" {
  source = "github.com/sentinelgrid/terraform-aws-sentinelgrid-integration"

  sentinelgrid_external_id    = var.sentinelgrid_external_id
  sentinelgrid_aws_account_id = var.sentinelgrid_aws_account_id

  enable_guardduty    = true
  enable_security_hub = true
  enable_config       = true
  enable_cloudtrail   = false # prefer existing org trail

  org_mode = true

  # Example: create helper log groups customers can route to
  create_flow_logs_log_group = true
  create_db_audit_log_group  = true

  # If you know destinations already:
  # additional_log_group_arns     = ["arn:aws:logs:us-east-1:<acct>:log-group:/aws/vpc/flow-logs:*"]
  # additional_s3_log_bucket_arns = ["arn:aws:s3:::my-flow-logs-bucket"]

  tags = {
    ManagedBy   = "SentinelGrid"
    Environment = "prod"
  }
}

output "monitor_role_arn" {
  value = module.sentinelgrid_integration.sentinelgrid_monitor_role_arn
}
