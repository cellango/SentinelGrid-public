# SentinelGrid AWS Integration - Outputs

output "sentinelgrid_monitor_role_arn" {
  description = "ARN of the IAM role for SentinelGrid monitoring (REQUIRED - paste this into SentinelGrid UI)"
  value       = aws_iam_role.sentinelgrid_monitor.arn
}

output "sentinelgrid_monitor_role_name" {
  description = "Name of the IAM role"
  value       = aws_iam_role.sentinelgrid_monitor.name
}

output "cloudtrail_trail_arn" {
  description = "ARN of the CloudTrail trail (if enabled)"
  value       = var.enable_cloudtrail ? aws_cloudtrail.sentinelgrid_trail[0].arn : null
}

output "cloudtrail_s3_bucket_arn" {
  description = "ARN of the S3 bucket used for CloudTrail logs (if created)"
  value       = var.enable_cloudtrail && var.cloudtrail_s3_bucket_name == null ? aws_s3_bucket.cloudtrail_bucket[0].arn : null
}

output "guardduty_detector_id" {
  description = "ID of the GuardDuty detector (if enabled)"
  value       = var.enable_guardduty ? aws_guardduty_detector.sentinelgrid_detector[0].id : null
}

output "config_recorder_name" {
  description = "Name of the AWS Config recorder (if enabled)"
  value       = var.enable_config ? aws_config_configuration_recorder.sentinelgrid_recorder[0].name : null
}

output "security_hub_arn" {
  description = "ARN of the Security Hub (if enabled)"
  value       = var.enable_security_hub ? aws_securityhub_account.sentinelgrid_security_hub[0].arn : null
}

output "aws_account_id" {
  description = "Current AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "flow_logs_log_group_arn" {
  description = "ARN of the Flow Logs log group (if created)"
  value       = var.create_flow_logs_log_group ? aws_cloudwatch_log_group.flow_logs[0].arn : null
}

output "db_audit_log_group_arn" {
  description = "ARN of the DB audit log group (if created)"
  value       = var.create_db_audit_log_group ? aws_cloudwatch_log_group.db_audit_logs[0].arn : null
}
