# SentinelGrid Agent CDN Infrastructure

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This Terraform module sets up the CDN infrastructure for distributing SentinelGrid agent packages.

## Features

- **S3 Bucket**: Stores agent packages with versioning
- **CloudFront Distribution**: Global CDN for fast package downloads
- **Public Access**: Configured for public read access
- **CORS**: Enabled for cross-origin requests
- **SSL/TLS**: Supports custom domain with ACM certificate
- **Logging**: Optional CloudFront access logging

## Requirements

- Terraform >= 1.0
- AWS Provider >= 5.0
- AWS account with appropriate permissions
- (Optional) ACM certificate in us-east-1 for custom domain

## Usage

### Basic Setup

```hcl
provider "aws" {
  region = "us-east-1"
}

module "cdn" {
  source = "./terraform/cdn"

  bucket_name        = "agents.sentinelgrid.ai"
  cloudfront_domain  = "agents.sentinelgrid.ai"
  certificate_arn    = "arn:aws:acm:us-east-1:123456789012:certificate/abc123..."
}
```

### Without Custom Domain

```hcl
module "cdn" {
  source = "./terraform/cdn"

  bucket_name = "agents-sentinelgrid-ai"
  # certificate_arn left empty - uses CloudFront default domain
}
```

## Outputs

- `bucket_name` - S3 bucket name
- `bucket_arn` - S3 bucket ARN
- `cloudfront_distribution_id` - CloudFront distribution ID
- `cloudfront_domain_name` - CloudFront domain name
- `cloudfront_url` - CloudFront URL
- `cdn_url` - CDN URL (custom domain if configured)

## Configuration

### Variables

- `bucket_name` - S3 bucket name (default: "agents.sentinelgrid.ai")
- `cloudfront_domain` - CloudFront domain name (default: "agents.sentinelgrid.ai")
- `certificate_arn` - ACM certificate ARN (optional)
- `enable_versioning` - Enable S3 versioning (default: true)
- `enable_logging` - Enable CloudFront logging (default: true)

## Security

- **Public Read**: Bucket policy allows public read access for packages
- **Encryption**: S3 bucket encryption enabled (AES256)
- **HTTPS**: CloudFront enforces HTTPS
- **CORS**: Configured for cross-origin requests

## Cost Optimization

- **Price Class**: Uses PriceClass_100 (North America and Europe only)
- **Caching**: Versioned packages cached for 7 days
- **Logging**: Optional, can be disabled to reduce costs

## Next Steps

After deploying:

1. Upload agent packages to S3 bucket
2. Configure DNS to point to CloudFront distribution (if using custom domain)
3. Test package downloads from CDN
4. Set up package repositories (APT/YUM) pointing to CDN

