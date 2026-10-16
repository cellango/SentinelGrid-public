# SentinelGrid AWS Integration - Main Configuration
# This module creates the necessary IAM role and policies for SentinelGrid to monitor your AWS account

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

locals {
  cloudtrail_bucket_name = coalesce(
    var.cloudtrail_s3_bucket_name,
    try(aws_s3_bucket.cloudtrail_bucket[0].id, null)
  )

  created_log_group_arns = compact([
    try(aws_cloudwatch_log_group.flow_logs[0].arn, ""),
    try(aws_cloudwatch_log_group.db_audit_logs[0].arn, "")
  ])

  log_group_arns = length(var.additional_log_group_arns) > 0 || length(local.created_log_group_arns) > 0 ?
    concat(var.additional_log_group_arns, local.created_log_group_arns) :
    ["*"]

  base_policy_statements = [
    # CloudTrail read access
    {
      Effect = "Allow"
      Action = [
        "cloudtrail:DescribeTrails",
        "cloudtrail:GetTrailStatus",
        "cloudtrail:GetEventSelectors",
        "cloudtrail:LookupEvents",
        "cloudtrail:GetTrail",
        "cloudtrail:ListTrails",
        "cloudtrail:GetInsightSelectors",
        "cloudtrail:ListInsights"
      ]
      Resource = "*"
    },
    # GuardDuty read access
    {
      Effect = "Allow"
      Action = [
        "guardduty:GetFindings",
        "guardduty:ListDetectors",
        "guardduty:ListFindings",
        "guardduty:GetDetector",
        "guardduty:DescribeOrganizationConfiguration",
        "guardduty:ListMembers",
        "guardduty:GetMembers"
      ]
      Resource = "*"
    },
    # AWS Config read access
    {
      Effect = "Allow"
      Action = [
        "config:Describe*",
        "config:Get*",
        "config:List*",
        "config:SelectResourceConfig"
      ]
      Resource = "*"
    },
    # Security Hub read access
    {
      Effect = "Allow"
      Action = [
        "securityhub:GetFindings",
        "securityhub:GetEnabledStandards",
        "securityhub:DescribeHub",
        "securityhub:ListFindings",
        "securityhub:BatchGetFindings",
        "securityhub:GetInsights",
        "securityhub:ListInsights"
      ]
      Resource = "*"
    },
    # IAM read access (for context)
    {
      Effect = "Allow"
      Action = [
        "iam:GetRole",
        "iam:ListRoles",
        "iam:GetUser",
        "iam:ListUsers",
        "iam:ListAccountAliases",
        "iam:GetAccountSummary",
        "iam:ListPolicies",
        "iam:GetPolicy",
        "iam:ListPolicyVersions"
      ]
      Resource = "*"
    },
    # VPC Flow Logs / app logs read access
    {
      Effect = "Allow"
      Action = [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ]
      Resource = local.log_group_arns
    },
    # CloudWatch metrics read access
    {
      Effect = "Allow"
      Action = [
        "cloudwatch:DescribeAlarms",
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics"
      ]
      Resource = "*"
    },
    # EC2 read access (for asset inventory)
    {
      Effect = "Allow"
      Action = [
        "ec2:DescribeInstances",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeVolumes",
        "ec2:DescribeSnapshots"
      ]
      Resource = "*"
    },
    # S3 bucket listing (for asset inventory)
    {
      Effect = "Allow"
      Action = [
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "s3:GetBucketAcl",
        "s3:GetBucketVersioning"
      ]
      Resource = "*"
    }
  ]

  extra_s3_log_statements = length(var.additional_s3_log_bucket_arns) > 0 ? [
    {
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = flatten([
        var.additional_s3_log_bucket_arns,
        [for b in var.additional_s3_log_bucket_arns : "${b}/*"]
      ])
    }
  ] : []

  cloudtrail_s3_statement = local.cloudtrail_bucket_name != null ? [
    {
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = [
        "arn:aws:s3:::${local.cloudtrail_bucket_name}",
        "arn:aws:s3:::${local.cloudtrail_bucket_name}/*"
      ]
      Condition = {
        StringLike = {
          "s3:prefix" = [
            "${var.cloudtrail_s3_bucket_prefix}/*"
          ]
        }
      }
    }
  ] : []
}

# ============================================================================
# IAM Role for SentinelGrid Monitoring
# ============================================================================

resource "aws_iam_role" "sentinelgrid_monitor" {
  name        = var.role_name
  description = "IAM role for SentinelGrid to monitor AWS account (read-only access)"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.sentinelgrid_aws_account_id}:root"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.sentinelgrid_external_id
          }
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "SentinelGrid Monitor Role"
      ManagedBy   = "SentinelGrid"
      Description = "Read-only monitoring role for SentinelGrid security platform"
    }
  )
}

# ============================================================================
# IAM Policy for SentinelGrid Monitoring
# ============================================================================

resource "aws_iam_role_policy" "sentinelgrid_monitor_policy" {
  name = "SentinelGridMonitorPolicy"
  role = aws_iam_role.sentinelgrid_monitor.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(local.base_policy_statements, local.cloudtrail_s3_statement, local.extra_s3_log_statements)
  })
}

# Optional helper log groups (placeholders; user must route logs)
resource "aws_cloudwatch_log_group" "flow_logs" {
  count             = var.create_flow_logs_log_group ? 1 : 0
  name              = var.flow_logs_log_group_name
  retention_in_days = var.flow_logs_log_group_retention_days
  tags = merge(
    var.tags,
    {
      Name      = "SentinelGrid Flow Logs"
      ManagedBy = "SentinelGrid"
    }
  )
}

resource "aws_cloudwatch_log_group" "db_audit_logs" {
  count             = var.create_db_audit_log_group ? 1 : 0
  name              = var.db_audit_log_group_name
  retention_in_days = var.db_audit_log_group_retention_days
  tags = merge(
    var.tags,
    {
      Name      = "SentinelGrid DB Audit Logs"
      ManagedBy = "SentinelGrid"
    }
  )
}

# ============================================================================
# CloudTrail Setup (Optional)
# ============================================================================

resource "aws_cloudtrail" "sentinelgrid_trail" {
  count = var.enable_cloudtrail ? 1 : 0

  name           = var.cloudtrail_name
  s3_bucket_name = var.cloudtrail_s3_bucket_name
  s3_key_prefix  = var.cloudtrail_s3_bucket_prefix

  include_global_service_events = true
  is_multi_region_trail         = true
  enable_logging                 = true
  enable_log_file_validation     = true

  event_selector {
    read_write_type                 = "All"
    include_management_events       = true
    exclude_management_event_sources = []

    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::*/*"]
    }

    data_resource {
      type   = "AWS::Lambda::Function"
      values = ["arn:aws:lambda:*"]
    }
  }

  tags = merge(
    var.tags,
    {
      Name      = "SentinelGrid CloudTrail"
      ManagedBy = "SentinelGrid"
    }
  )

  depends_on = [aws_s3_bucket_policy.cloudtrail_bucket_policy]
}

# S3 bucket for CloudTrail (if not provided)
resource "aws_s3_bucket" "cloudtrail_bucket" {
  count = var.enable_cloudtrail && var.cloudtrail_s3_bucket_name == null ? 1 : 0

  bucket        = "${var.cloudtrail_s3_bucket_name_prefix}-${data.aws_caller_identity.current.account_id}"
  force_destroy = false

  tags = merge(
    var.tags,
    {
      Name      = "SentinelGrid CloudTrail Logs"
      ManagedBy = "SentinelGrid"
    }
  )
}

resource "aws_s3_bucket_versioning" "cloudtrail_bucket_versioning" {
  count = var.enable_cloudtrail && var.cloudtrail_s3_bucket_name == null ? 1 : 0

  bucket = aws_s3_bucket.cloudtrail_bucket[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudtrail_bucket_encryption" {
  count = var.enable_cloudtrail && var.cloudtrail_s3_bucket_name == null ? 1 : 0

  bucket = aws_s3_bucket.cloudtrail_bucket[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "cloudtrail_bucket_pab" {
  count = var.enable_cloudtrail && var.cloudtrail_s3_bucket_name == null ? 1 : 0

  bucket = aws_s3_bucket.cloudtrail_bucket[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "cloudtrail_bucket_policy" {
  count = var.enable_cloudtrail ? 1 : 0

  bucket = var.cloudtrail_s3_bucket_name != null ? var.cloudtrail_s3_bucket_name : aws_s3_bucket.cloudtrail_bucket[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = "arn:aws:s3:::${var.cloudtrail_s3_bucket_name != null ? var.cloudtrail_s3_bucket_name : aws_s3_bucket.cloudtrail_bucket[0].id}"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = "arn:aws:cloudtrail:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:trail/${var.cloudtrail_name}"
          }
        }
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "arn:aws:s3:::${var.cloudtrail_s3_bucket_name != null ? var.cloudtrail_s3_bucket_name : aws_s3_bucket.cloudtrail_bucket[0].id}/${var.cloudtrail_s3_bucket_prefix}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = "arn:aws:cloudtrail:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:trail/${var.cloudtrail_name}"
            "s3:x-amz-acl"  = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

data "aws_region" "current" {}

# ============================================================================
# GuardDuty Setup (Optional)
# ============================================================================

resource "aws_guardduty_detector" "sentinelgrid_detector" {
  count = var.enable_guardduty ? 1 : 0

  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"

  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }

  tags = merge(
    var.tags,
    {
      Name      = "SentinelGrid GuardDuty Detector"
      ManagedBy = "SentinelGrid"
    }
  )
}

# ============================================================================
# AWS Config Setup (Optional)
# ============================================================================

resource "aws_config_configuration_recorder" "sentinelgrid_recorder" {
  count = var.enable_config ? 1 : 0

  name     = "sentinelgrid-config-recorder"
  role_arn = aws_iam_role.config_recorder[0].arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }

  depends_on = [aws_config_delivery_channel.sentinelgrid_delivery_channel]
}

resource "aws_config_delivery_channel" "sentinelgrid_delivery_channel" {
  count = var.enable_config ? 1 : 0

  name           = "sentinelgrid-delivery-channel"
  s3_bucket_name = var.config_s3_bucket_name != null ? var.config_s3_bucket_name : aws_s3_bucket.config_bucket[0].id
  s3_key_prefix  = var.config_s3_bucket_prefix
}

resource "aws_config_configuration_recorder_status" "sentinelgrid_recorder_status" {
  count = var.enable_config ? 1 : 0

  name       = aws_config_configuration_recorder.sentinelgrid_recorder[0].name
  is_enabled = true

  depends_on = [aws_config_delivery_channel.sentinelgrid_delivery_channel]
}

# IAM role for Config recorder
resource "aws_iam_role" "config_recorder" {
  count = var.enable_config ? 1 : 0

  name = "sentinelgrid-config-recorder-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "config_recorder_policy" {
  count = var.enable_config ? 1 : 0

  role       = aws_iam_role.config_recorder[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/ConfigRole"
}

# S3 bucket for Config (if not provided)
resource "aws_s3_bucket" "config_bucket" {
  count = var.enable_config && var.config_s3_bucket_name == null ? 1 : 0

  bucket        = "${var.config_s3_bucket_name_prefix}-${data.aws_caller_identity.current.account_id}"
  force_destroy = false

  tags = merge(
    var.tags,
    {
      Name      = "SentinelGrid Config"
      ManagedBy = "SentinelGrid"
    }
  )
}

# ============================================================================
# Security Hub Setup (Optional)
# ============================================================================

resource "aws_securityhub_account" "sentinelgrid_security_hub" {
  count = var.enable_security_hub ? 1 : 0

  enable_default_standards = true
}

# Enable CIS AWS Foundations Benchmark
resource "aws_securityhub_standards_subscription" "cis_benchmark" {
  count = var.enable_security_hub ? 1 : 0

  standards_arn = "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"

  depends_on = [aws_securityhub_account.sentinelgrid_security_hub]
}
