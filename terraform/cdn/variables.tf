# SentinelGrid CDN - Variables

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

