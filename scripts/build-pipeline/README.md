# Build Pipeline Scripts

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains scripts for the hardened image build pipeline.

## Scripts

### `validate-packer-template.sh`

Validates Packer templates before building.

**Usage:**
```bash
./scripts/build-pipeline/validate-packer-template.sh packer/amazon-linux-2/aws/amazon-linux-2.json
```

**Checks:**
- JSON syntax validation
- Packer template validation
- Required fields (builders, provisioners)
- CIS hardening script references
- Agent installation script references

### `distribute-images.sh`

Distributes/shares hardened images to specified accounts.

**Usage:**
```bash
# AWS
./scripts/build-pipeline/distribute-images.sh aws ami-1234567890abcdef0 "123456789012,987654321098"

# Azure
./scripts/build-pipeline/distribute-images.sh azure "/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/xxx" "sub-id-1,sub-id-2"

# GCP
./scripts/build-pipeline/distribute-images.sh gcp "projects/xxx/global/images/xxx" "project-1,project-2"
```

## GitHub Actions Workflows

### `build-hardened-images.yml`

Main workflow for building hardened images.

**Triggers:**
- Weekly schedule (Sunday 2 AM UTC)
- Manual dispatch with options:
  - OS selection (all, amazon-linux-2, ubuntu-22.04, etc.)
  - Cloud selection (all, aws, azure, gcp)
  - Agent version

**Jobs:**
- `build-aws` - Builds AWS AMIs
- `build-azure` - Builds Azure Images
- `build-gcp` - Builds GCP Images
- `update-registry` - Updates image registry database
- `notify` - Sends notifications

### `test-hardened-images.yml`

Workflow for testing built images.

**Triggers:**
- After successful build workflow
- Manual dispatch with image ID

**Jobs:**
- `test-aws` - Tests AWS AMIs
- `test-azure` - Tests Azure Images
- `test-gcp` - Tests GCP Images

## Required Secrets

### AWS
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SHARE_ACCOUNTS` (optional, comma-separated)

### Azure
- `AZURE_CREDENTIALS` (JSON with client_id, client_secret, subscription_id, tenant_id)
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_TENANT_ID`
- `AZURE_RESOURCE_GROUP`

### GCP
- `GCP_SA_KEY` (Service account JSON key)
- `GCP_PROJECT_ID`

### General
- `SENTINELGRID_TENANT_TOKEN` (for agent configuration)
- `DB_URL` (for image registry updates)
- `SLACK_WEBHOOK_URL` (optional, for notifications)

## Usage

### Manual Build

```bash
# Build all images
gh workflow run build-hardened-images.yml

# Build specific OS on AWS
gh workflow run build-hardened-images.yml \
  -f os=amazon-linux-2 \
  -f cloud=aws \
  -f agent_version=1.0.0
```

### Manual Test

```bash
gh workflow run test-hardened-images.yml \
  -f image_id=ami-1234567890abcdef0 \
  -f cloud=aws \
  -f os=amazon-linux-2
```

## Monitoring

- Build logs are uploaded as artifacts
- Manifests are stored for 90 days
- Notifications sent via Slack (if configured)

## Troubleshooting

### Build Fails

1. Check Packer logs in artifacts
2. Verify cloud provider credentials
3. Check source image availability
4. Review template validation

### Test Fails

1. Verify test instance can launch
2. Check network connectivity
3. Review test script output
4. Check security group/firewall rules

