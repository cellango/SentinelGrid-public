# SentinelGrid CDN - Outputs

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

