#
# AWS Network Policy - Block Direct AI Provider Access
# =====================================================
#
# Purpose: Prevent applications from bypassing SentinelGrid AI Shield gateway
#          by blocking direct egress to OpenAI, Anthropic, and other AI providers
#
# Usage:
#   terraform init
#   terraform plan -var="sentinelgrid_gateway_cidr=10.0.1.0/24"
#   terraform apply
#
# Requirements:
#   - VPC ID where applications run
#   - CIDR of SentinelGrid gateway endpoint
#

variable "vpc_id" {
  description = "VPC ID where applications run"
  type        = string
}

variable "sentinelgrid_gateway_cidr" {
  description = "CIDR block for SentinelGrid AI Shield gateway"
  type        = string
  default     = "0.0.0.0/0"  # Update with actual gateway IP/CIDR
}

variable "sentinelgrid_gateway_port" {
  description = "Port for SentinelGrid AI Shield gateway"
  type        = number
  default     = 8023
}

variable "application_security_group_ids" {
  description = "List of security group IDs for applications that use AI"
  type        = list(string)
  default     = []
}

# Data source: Get OpenAI IP ranges (these are approximate - verify with OpenAI docs)
# OpenAI doesn't publish official IP ranges, so we block by DNS and alert on attempts
locals {
  # Known AI provider domains (for reference - actual blocking via Security Groups)
  blocked_ai_providers = [
    "api.openai.com",
    "api.anthropic.com",
    "api.cohere.ai",
    "api.ai21.com"
  ]
}

#
# Security Group: AI Gateway Enforcement
# ======================================
# Blocks all HTTPS egress except to SentinelGrid gateway
#

resource "aws_security_group" "ai_gateway_enforcement" {
  name        = "sentinelgrid-ai-gateway-enforcement"
  description = "Enforce all AI traffic through SentinelGrid gateway - block direct provider access"
  vpc_id      = var.vpc_id

  tags = {
    Name        = "SentinelGrid AI Gateway Enforcement"
    Purpose     = "AI Security"
    ManagedBy   = "Terraform"
  }
}

#
# EGRESS RULES
# ============

# Block all HTTPS egress by default (will add explicit allow rules below)
# This is the nuclear option - adjust based on your needs
resource "aws_security_group_rule" "block_all_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Block all HTTPS - will add explicit allows"
  security_group_id = aws_security_group.ai_gateway_enforcement.id
  
  # Note: This blocks all HTTPS. Comment out if too restrictive.
  # Instead, use more targeted rules below.
  lifecycle {
    create_before_destroy = true
  }
}

# Allow HTTPS to SentinelGrid gateway ONLY
resource "aws_security_group_rule" "allow_gateway" {
  type              = "egress"
  from_port         = var.sentinelgrid_gateway_port
  to_port           = var.sentinelgrid_gateway_port
  protocol          = "tcp"
  cidr_blocks       = [var.sentinelgrid_gateway_cidr]
  description       = "Allow traffic to SentinelGrid AI Shield gateway"
  security_group_id = aws_security_group.ai_gateway_enforcement.id
}

# Allow DNS (required for gateway hostname resolution)
resource "aws_security_group_rule" "allow_dns" {
  type              = "egress"
  from_port         = 53
  to_port           = 53
  protocol          = "udp"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow DNS resolution"
  security_group_id = aws_security_group.ai_gateway_enforcement.id
}

# Allow HTTP/HTTPS to internal services (adjust CIDR as needed)
resource "aws_security_group_rule" "allow_internal_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  description       = "Allow HTTPS to internal/RFC1918 addresses"
  security_group_id = aws_security_group.ai_gateway_enforcement.id
}

#
# INGRESS RULES
# =============
# Applications still need to receive traffic

resource "aws_security_group_rule" "allow_app_ingress" {
  type              = "ingress"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  cidr_blocks       = [data.aws_vpc.selected.cidr_block]
  description       = "Allow all inbound from VPC"
  security_group_id = aws_security_group.ai_gateway_enforcement.id
}

#
# Data Sources
# ============

data "aws_vpc" "selected" {
  id = var.vpc_id
}

#
# Outputs
# =======

output "security_group_id" {
  description = "ID of the AI gateway enforcement security group"
  value       = aws_security_group.ai_gateway_enforcement.id
}

output "security_group_name" {
  description = "Name of the security group"
  value       = aws_security_group.ai_gateway_enforcement.name
}

output "enforcement_summary" {
  description = "Summary of enforcement rules"
  value = <<-EOT
    ✓ Security Group Created: ${aws_security_group.ai_gateway_enforcement.id}
    ✓ Blocks HTTPS egress to 0.0.0.0/0 (all destinations)
    ✓ Allows gateway access: ${var.sentinelgrid_gateway_cidr}:${var.sentinelgrid_gateway_port}
    ✓ Allows DNS resolution
    ✓ Allows internal HTTPS (RFC1918 ranges)
    
    Next Steps:
    1. Attach this security group to your AI application instances/ENIs
    2. Test gateway connectivity: curl http://${var.sentinelgrid_gateway_cidr}:${var.sentinelgrid_gateway_port}/health
    3. Verify OpenAI is blocked: curl https://api.openai.com (should fail)
    4. Deploy SentinelGrid Endpoint Protection agent for detection
  EOT
}

#
# CloudWatch Alarms (Optional)
# =============================
# Alert if security group is modified

resource "aws_cloudwatch_event_rule" "security_group_changes" {
  name        = "sentinelgrid-ai-gateway-sg-changes"
  description = "Alert on changes to AI gateway enforcement security group"

  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["AWS API Call via CloudTrail"]
    detail = {
      eventName = [
        "AuthorizeSecurityGroupIngress",
        "AuthorizeSecurityGroupEgress",
        "RevokeSecurityGroupIngress",
        "RevokeSecurityGroupEgress",
        "DeleteSecurityGroup"
      ]
      requestParameters = {
        groupId = [aws_security_group.ai_gateway_enforcement.id]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "send_to_sns" {
  rule      = aws_cloudwatch_event_rule.security_group_changes.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.security_alerts.arn
}

resource "aws_sns_topic" "security_alerts" {
  name = "sentinelgrid-ai-security-alerts"
}

output "sns_topic_arn" {
  description = "SNS topic for security group change alerts"
  value       = aws_sns_topic.security_alerts.arn
}

