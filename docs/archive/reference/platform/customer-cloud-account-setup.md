# Customer Cloud Account Setup Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This guide explains how customers can provide their cloud account information for hardened image sharing.

## Overview

To receive SentinelGrid hardened images, customers need to provide their cloud provider account information. This allows us to share images directly to your accounts.

## Supported Cloud Providers

- **AWS**: Amazon Web Services
- **Azure**: Microsoft Azure
- **GCP**: Google Cloud Platform

## Required Information

### AWS

- **Account ID**: 12-digit AWS account ID
- **Regions**: List of regions where you want images (e.g., us-east-1, us-west-2)

### Azure

- **Subscription ID**: Azure subscription UUID
- **Regions**: List of regions (e.g., East US, West US)

### GCP

- **Project ID**: GCP project identifier
- **Regions**: List of regions (e.g., us-east1, us-west1)

## Setup Methods

### Method 1: During Onboarding

If you're a new customer, cloud account information is collected during onboarding:

```bash
# Run onboarding script
./infra/shared/scripts/onboard-customer-images.sh <tenant_id> <tenant_name>
```

### Method 2: Via API

```bash
# Register AWS account
curl -X POST https://api.sentinelgrid.ai/api/v1/admin/customer-cloud-accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "your-tenant-id",
    "cloud_provider": "aws",
    "account_id": "123456789012",
    "regions": ["us-east-1", "us-west-2"],
    "version_policy": "latest"
  }'
```

### Method 3: Manual Database Entry

Contact support to manually register your accounts.

## Version Policy

Choose your version policy:

- **latest** (Recommended): Always receive the latest image versions
- **stable**: Receive only stable versions (skip beta releases)
- **pinned**: Pin to a specific version

## Security

### Account Permissions

For image sharing, we need:
- **AWS**: Permission to modify AMI launch permissions
- **Azure**: Access to share images (via resource groups or subscriptions)
- **GCP**: IAM permissions to share images

### Best Practices

1. Use dedicated accounts/subscriptions for image sharing if possible
2. Review shared images before use
3. Monitor image access logs
4. Rotate credentials regularly

## Verification

After providing account information:

1. **Confirmation Email**: You'll receive confirmation
2. **Dashboard**: Check dashboard for registered accounts
3. **Test Share**: We'll share a test image to verify access

## Updating Account Information

### Add Regions

```bash
# Update regions via API
curl -X PUT https://api.sentinelgrid.ai/api/v1/admin/customer-cloud-accounts/{account_id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"regions": ["us-east-1", "us-west-2", "eu-west-1"]}'
```

### Change Version Policy

Contact support or use API to update version policy.

### Remove Account

```bash
# Deactivate account
curl -X PUT https://api.sentinelgrid.ai/api/v1/admin/customer-cloud-accounts/{account_id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status": "inactive"}'
```

## Troubleshooting

### Images Not Appearing

1. Verify account ID is correct
2. Check account permissions
3. Verify regions are correct
4. Contact support

### Access Denied

1. Check IAM permissions
2. Verify account is active
3. Review cloud provider logs

## Support

For assistance:
- Email: support@sentinelgrid.ai
- Documentation: https://docs.sentinelgrid.ai
- API: https://api.sentinelgrid.ai/api/v1/customer-cloud-accounts

