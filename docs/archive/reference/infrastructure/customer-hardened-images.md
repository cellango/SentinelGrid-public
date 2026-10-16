# Customer Hardened Images Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This guide explains how customers can use SentinelGrid hardened OS images.

## Overview

SentinelGrid provides pre-built, hardened OS images with:
- CIS Level 1 or Level 2 hardening applied
- SentinelGrid Endpoint Protection Agent pre-installed
- Security scanned and validated
- Available for AWS, Azure, and GCP

## Available Images

### Supported Operating Systems

- **Amazon Linux 2** (CIS Level 1)
- **Ubuntu 22.04 LTS** (CIS Level 1)
- **RHEL 8** (CIS Level 1)
- **Debian 12** (CIS Level 1)
- **Windows Server 2022** (CIS Level 1)

### Cloud Providers

- **AWS**: AMIs available in multiple regions
- **Azure**: Managed Images available
- **GCP**: Compute Engine Images available

## Finding Images

### Via API

```bash
# List available images
curl https://api.sentinelgrid.ai/api/v1/hardened-images?cloud_provider=aws

# Get recommended images
curl https://api.sentinelgrid.ai/api/v1/hardened-images/recommendations/list?cloud_provider=aws&region=us-east-1
```

### Via Cloud Console

Images shared to your account will appear in:
- **AWS**: EC2 → AMIs → Private images
- **Azure**: Virtual Machines → Images
- **GCP**: Compute Engine → Images

## Using Images

### AWS

1. Navigate to EC2 → Launch Instance
2. Select "My AMIs" or "Private images"
3. Find SentinelGrid hardened image
4. Launch instance as normal

```bash
# Via AWS CLI
aws ec2 run-instances \
    --image-id ami-xxxxxxxxxxxxx \
    --instance-type t3.medium \
    --key-name your-key-pair
```

### Azure

1. Navigate to Virtual Machines → Create
2. Select "Browse all public and private images"
3. Find SentinelGrid hardened image
4. Create VM as normal

```bash
# Via Azure CLI
az vm create \
    --resource-group my-resource-group \
    --name my-vm \
    --image /subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/sentinelgrid-ubuntu-22.04-hardened
```

### GCP

1. Navigate to Compute Engine → VM instances → Create
2. Click "Change" under Boot disk
3. Select "Custom images" tab
4. Find SentinelGrid hardened image
5. Create VM as normal

```bash
# Via gcloud CLI
gcloud compute instances create my-instance \
    --image=projects/sentinelgrid/global/images/sentinelgrid-ubuntu-22-04-hardened \
    --zone=us-east1-b
```

## Post-Launch Configuration

### Agent Configuration

The agent is pre-installed but needs to be configured with your tenant token:

```bash
# Linux
sudo /var/ossec/bin/agent-auth -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN
sudo systemctl restart sentinelgrid-agent

# Windows (PowerShell)
& "C:\Program Files (x86)\ossec-agent\agent-auth.exe" -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN
Restart-Service "SentinelGrid Agent"
```

### Verify Hardening

```bash
# Check CIS compliance (example for Linux)
sudo /opt/sentinelgrid/scripts/verify-hardening.sh
```

## Image Updates

When new image versions are available:
1. You'll be notified via email or dashboard
2. New images are automatically shared to your account
3. Launch new instances from updated images
4. Migrate existing workloads as needed

## Version Policy

You can configure your version policy:
- **latest**: Always use latest version (recommended)
- **stable**: Use latest stable version (skip beta)
- **pinned**: Pin to specific version

Contact support to change your version policy.

## Security Scanning

All images are security scanned before distribution:
- Vulnerability scanning
- Compliance validation
- Agent installation verification

Only images that pass all scans are made available.

## Support

For issues or questions:
- Email: support@sentinelgrid.ai
- Documentation: https://docs.sentinelgrid.ai
- API: https://api.sentinelgrid.ai/api/v1/hardened-images

