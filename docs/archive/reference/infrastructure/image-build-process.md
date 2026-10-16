# Hardened Image Build Process

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document describes the step-by-step process for building hardened OS images with Packer.

## Overview

The image build process includes:
1. Building image with Packer
2. Security scanning
3. Validation
4. Registration in database
5. Distribution to customers

## Prerequisites

- Packer installed (>= 1.8.0)
- Cloud provider CLI tools (AWS CLI, Azure CLI, gcloud)
- Cloud provider credentials configured
- CIS hardening scripts available
- Agent packages available in CDN

## Build Steps

### 1. Ensure Agents Are Available

Before building images, ensure the agent version is available in CDN:

```bash
# Check agent availability
curl -I https://agents.sentinelgrid.ai/v1.0.0/linux/rpm/sentinelgrid-agent-1.0.0-1.x86_64.rpm
```

### 2. Build Image

```bash
cd scripts/build-pipeline
./build-image.sh amazon-linux-2 aws 1.0.0
```

This:
- Validates agent availability
- Runs Packer build
- Applies CIS hardening
- Installs SentinelGrid agent
- Creates image in cloud provider

### 3. Scan Image

```bash
./scan-image.sh aws ami-xxxxxxxxxxxxx amazon-linux-2
```

Performs security scanning:
- Vulnerability scanning
- Compliance validation
- Generates scan results JSON

### 4. Parse Scan Results

```bash
./parse-scan-results.sh /tmp/sentinelgrid-scan-ami-xxxxxxxxxxxxx.json
```

Validates scan results against security policy.

### 5. Validate Image

```bash
./validate-image.sh aws ami-xxxxxxxxxxxxx amazon-linux-2
```

Validates:
- Agent is installed
- Hardening is applied
- Image is accessible

### 6. Register Image

```bash
./register-image.sh aws ami-xxxxxxxxxxxxx amazon-linux-2 2023 1.0.0 cis-level1 /tmp/sentinelgrid-scan-ami-xxxxxxxxxxxxx.json
```

Registers image in database with:
- Version information
- Scan results
- Metadata

### 7. Distribute Image

```bash
./distribute-images.sh aws ami-xxxxxxxxxxxxx
```

Shares image with customer accounts (only if scan passed).

## Complete Workflow

```bash
#!/bin/bash
# Complete image build workflow

OS_TYPE="amazon-linux-2"
CLOUD="aws"
AGENT_VERSION="1.0.0"

# Build
./build-image.sh "$OS_TYPE" "$CLOUD" "$AGENT_VERSION"

# Get image ID from Packer manifest
IMAGE_ID=$(jq -r '.builds[0].artifact_id' packer/manifest.json | cut -d: -f2)

# Scan
./scan-image.sh "$CLOUD" "$IMAGE_ID" "$OS_TYPE"
SCAN_RESULT="/tmp/sentinelgrid-scan-${IMAGE_ID}.json"

# Validate scan
if ./parse-scan-results.sh "$SCAN_RESULT"; then
    # Register
    ./register-image.sh "$CLOUD" "$IMAGE_ID" "$OS_TYPE" "" "$AGENT_VERSION" "cis-level1" "$SCAN_RESULT"
    
    # Distribute
    ./distribute-images.sh "$CLOUD" "$IMAGE_ID"
else
    echo "❌ Scan failed - Image not distributed"
    exit 1
fi
```

## Packer Templates

Packer templates are located in `packer/{os-type}/{cloud-provider}/`:

- `amazon-linux-2/aws/amazon-linux-2.json`
- `ubuntu-22.04/aws/ubuntu-22.04.json`
- `rhel-8/azure/rhel-8.json`
- etc.

### Template Variables

- `sentinelgrid_agent_version`: Agent version to install
- `sentinelgrid_tenant_token`: Optional tenant token
- `sentinelgrid_manager_host`: Manager hostname
- `ami_users`: AWS account IDs to share with (for AWS)

## Security Scanning

### AWS

Uses AWS Inspector v2 or EC2 Image Builder for scanning.

### Azure

Uses Azure Security Center or Defender for Cloud.

### GCP

Uses Container Analysis API or Cloud Security Command Center.

### Security Policy

Images must meet these thresholds:
- **Critical vulnerabilities**: 0
- **High vulnerabilities**: ≤ 5
- **Medium vulnerabilities**: ≤ 20
- **Low vulnerabilities**: ≤ 50

## Version Management

### Image Versioning

Images use semantic versioning:
- Format: `{os-type}-{os-version}-{hardening-level}-agent-{agent-version}-{build-number}`
- Example: `amazon-linux-2-2023-cis-level1-agent-1.0.0-build-42`

### Release Process

```bash
# Mark as latest
./scripts/version-management/release-version.sh image 1.0.0 amazon-linux-2 aws
```

## Automation

Builds can be automated via CI/CD:

```yaml
# .github/workflows/build-images.yml
name: Build Hardened Images

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Image
        run: ./scripts/build-pipeline/build-image.sh ubuntu-22.04 aws 1.0.0
      - name: Scan Image
        run: ./scripts/build-pipeline/scan-image.sh aws $IMAGE_ID ubuntu-22.04
      - name: Register Image
        run: ./scripts/build-pipeline/register-image.sh aws $IMAGE_ID ubuntu-22.04
```

## Troubleshooting

### Build Fails

- Check Packer is installed
- Verify cloud provider credentials
- Check source image availability
- Review Packer logs

### Scan Fails

- Verify scanning tools are configured
- Check image accessibility
- Review scan logs

### Distribution Fails

- Verify customer accounts are registered
- Check cloud provider permissions
- Review distribution logs

## Support

For issues or questions, contact the DevOps team.

