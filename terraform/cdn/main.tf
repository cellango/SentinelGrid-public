# SentinelGrid Agent CDN Infrastructure
# Creates S3 bucket, CloudFront distribution, and related resources

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "bucket_name" {
  type        = string
  description = "S3 bucket name for agent packages"
  default     = "agents.sentinelgrid.ai"
}

variable "cloudfront_domain" {
  type        = string
  description = "CloudFront domain name"
  default     = "agents.sentinelgrid.ai"
}

variable "certificate_arn" {
  type        = string
  description = "ACM certificate ARN for CloudFront (must be in us-east-1)"
  default     = ""
}

variable "enable_versioning" {
  type        = bool
  description = "Enable S3 bucket versioning"
  default     = true
}

variable "enable_logging" {
  type        = bool
  description = "Enable CloudFront access logging"
  default     = true
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ============================================================================
# S3 Bucket for Agent Packages
# ============================================================================

resource "aws_s3_bucket" "agents" {
  bucket = var.bucket_name

  tags = {
    Name        = "SentinelGrid Agent Packages"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket_versioning" "agents" {
  bucket = aws_s3_bucket.agents.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "agents" {
  bucket = aws_s3_bucket.agents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "agents" {
  bucket = aws_s3_bucket.agents.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Bucket policy for public read access
resource "aws_s3_bucket_policy" "agents" {
  bucket = aws_s3_bucket.agents.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.agents.arn}/*"
      }
    ]
  })
}

# CORS configuration
resource "aws_s3_bucket_cors_configuration" "agents" {
  bucket = aws_s3_bucket.agents.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag", "Content-Length", "Content-Type"]
    max_age_seconds = 3600
  }
}

# ============================================================================
# CloudFront Distribution
# ============================================================================

resource "aws_cloudfront_origin_access_control" "agents" {
  name                              = "sentinelgrid-agents-oac"
  description                       = "OAC for SentinelGrid agent packages"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "agents" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "SentinelGrid Agent Packages CDN"
  default_root_object = "index.html"
  price_class         = "PriceClass_100" # Use only North America and Europe

  aliases = var.certificate_arn != "" ? [var.cloudfront_domain] : []

  origin {
    domain_name              = aws_s3_bucket.agents.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.agents.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.agents.id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.agents.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # Cache behavior for versioned paths
  ordered_cache_behavior {
    path_pattern     = "/v*/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.agents.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 86400  # Cache versioned packages longer
    default_ttl            = 86400
    max_ttl                = 604800  # 7 days
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = var.certificate_arn != "" ? var.certificate_arn : null
    ssl_support_method       = var.certificate_arn != "" ? "sni-only" : "vip"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name        = "SentinelGrid Agents CDN"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# CloudFront Logging (Optional)
# ============================================================================

resource "aws_s3_bucket" "cloudfront_logs" {
  count  = var.enable_logging ? 1 : 0
  bucket = "${var.bucket_name}-logs"

  tags = {
    Name        = "SentinelGrid CloudFront Logs"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "cloudfront_logs" {
  count  = var.enable_logging ? 1 : 0
  bucket = aws_s3_bucket.cloudfront_logs[0].id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

# ============================================================================
# Outputs
# ============================================================================

output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.agents.id
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.agents.arn
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.agents.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.agents.domain_name
}

output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${aws_cloudfront_distribution.agents.domain_name}"
}

output "cdn_url" {
  description = "CDN URL (with custom domain if configured)"
  value       = var.certificate_arn != "" ? "https://${var.cloudfront_domain}" : "https://${aws_cloudfront_distribution.agents.domain_name}"
}

