# SentinelGrid AWS Integration - Terraform Module

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This Terraform module sets up the necessary AWS resources for SentinelGrid to monitor your AWS account with read-only access.

## Features

- **IAM Role**: Cross-account role for SentinelGrid with read-only permissions
- **CloudTrail** (Optional): Multi-region CloudTrail trail for audit logging
- **GuardDuty** (Optional): Threat detection service
- **AWS Config** (Optional): Configuration compliance monitoring
- **Security Hub** (Optional): Centralized security findings
- **Extra log access (optional)**: Allow read access to additional CloudWatch Log Groups or S3 log buckets (e.g., VPC Flow Logs, ALB/WAF/Lambda, DB audit dumps)
- **Helper log groups (optional)**: Create placeholder CloudWatch Log Groups for Flow Logs and DB audit logs (you still enable the sources to write there)
- **Org ready (guidance)**: Module is single-account; wrap with StackSets for org/OU rollout

## Requirements

- Terraform >= 1.0
- AWS Provider >= 5.0
- AWS Account with appropriate permissions

## Usage

### Basic Setup (IAM Role Only)

```hcl
module "sentinelgrid_integration" {
  source = "github.com/sentinelgrid/terraform-aws-sentinelgrid-integration"

  sentinelgrid_external_id      = "550e8400-e29b-41d4-a716-446655440000"
  sentinelgrid_aws_account_id   = "987654321098"
}
```

### Full Setup (All Services)

```hcl
module "sentinelgrid_integration" {
  source = "github.com/sentinelgrid/terraform-aws-sentinelgrid-integration"

  sentinelgrid_external_id      = "550e8400-e29b-41d4-a716-446655440000"
  sentinelgrid_aws_account_id   = "987654321098"
  
  enable_cloudtrail    = true
  enable_guardduty     = true
  enable_config        = true
  enable_security_hub  = true
  additional_log_group_arns     = ["arn:aws:logs:us-east-1:123456789012:log-group:/aws/vpc/flow-logs:*"]
  additional_s3_log_bucket_arns = ["arn:aws:s3:::my-flow-logs-bucket"]
  create_flow_logs_log_group    = true
  create_db_audit_log_group     = true
  
  tags = {
    Environment = "production"
    ManagedBy   = "SentinelGrid"
  }
}
```

### Org/StackSet Wrapper (guidance)
- This module is single-account; for Organizations, wrap with StackSets/OU targeting.
- Example scaffolding is in `examples/org-stackset-wrapper/main.tf` (illustrative; use `aws_cloudformation_stack_set` for full org rollout).

## Getting Your External ID

1. Log in to SentinelGrid
2. Go to Onboarding → Connect AWS
3. Copy the External ID shown
4. Use it in the `sentinelgrid_external_id` variable

## Outputs

After applying, you'll get:

- `sentinelgrid_monitor_role_arn` - **REQUIRED**: Paste this into the SentinelGrid UI
- `cloudtrail_trail_arn` - CloudTrail trail ARN (if enabled)
- `guardduty_detector_id` - GuardDuty detector ID (if enabled)
- Other optional outputs

## Permissions

The IAM role created has **read-only** permissions for:

- CloudTrail (audit logs)
- GuardDuty (threat findings)
- AWS Config (compliance data)
- Security Hub (security findings)
- S3 (CloudTrail log buckets; optional additional log buckets if provided)
- IAM (read-only for context)
- EC2 (asset inventory)
- CloudWatch Logs (VPC Flow Logs, and any additional log group ARNs you supply)

## Org/StackSet usage (guidance)
- This module deploys into a single account. To cover an Organization, wrap it with a StackSet (target OUs/accounts) or a pipeline that iterates accounts/regions.
- ExternalId should be per-tenant; reuse across accounts for the same tenant to simplify UI input.
- When using StackSets, set `org_mode = true` (informational) and supply the region set you deploy to.

**No write, delete, or modify permissions are granted.**

## Security

- **External ID**: Required for cross-account role assumption (prevents confused deputy attacks)
- **Least Privilege**: Only read-only permissions
- **Resource Scoping**: S3 permissions limited to CloudTrail buckets
- **Encryption**: CloudTrail logs encrypted at rest

## Examples

See the `examples/` directory for more usage examples.

## Support

For issues or questions, contact SentinelGrid support or open an issue in the repository.

## License

This module is provided as-is by SentinelGrid.
