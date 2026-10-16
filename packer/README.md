# SentinelGrid Hardened Image Packer Templates

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


This directory contains Packer templates for building hardened OS images with SentinelGrid Endpoint Protection Agent pre-installed.

## Supported Operating Systems

1. **Amazon Linux 2** - `amazon-linux-2/`
2. **Ubuntu 22.04 LTS** - `ubuntu-22.04/`
3. **RHEL 8** - `rhel-8/`
4. **Debian 12** - `debian-12/`
5. **Windows Server 2022** - `windows-server-2022/`

## Supported Cloud Providers

- **AWS** - Amazon Machine Images (AMIs)
- **Azure** - Managed Images
- **GCP** - Compute Engine Images

## Prerequisites

1. **Packer** - Install Packer >= 1.8.0
   ```bash
   # macOS
   brew install packer
   
   # Linux
   wget https://releases.hashicorp.com/packer/1.9.4/packer_1.9.4_linux_amd64.zip
   unzip packer_1.9.4_linux_amd64.zip
   sudo mv packer /usr/local/bin/
   ```

2. **Cloud Provider Credentials**
   - **AWS**: Configure `~/.aws/credentials` or set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
   - **Azure**: Set `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`
   - **GCP**: Set `GOOGLE_APPLICATION_CREDENTIALS` or use `gcloud auth application-default login`

3. **SentinelGrid Agent** - Agent packages must be available in CDN or repositories

## Usage

### AWS Example (Amazon Linux 2)

```bash
cd packer/amazon-linux-2/aws

# Build with variables
packer build \
  -var 'aws_region=us-east-1' \
  -var 'source_ami=ami-0c02fb55956c7d316' \
  -var 'sentinelgrid_agent_version=1.0.0' \
  -var 'sentinelgrid_tenant_token=your-token-here' \
  amazon-linux-2.json
```

### Azure Example (Ubuntu 22.04)

```bash
cd packer/ubuntu-22.04/azure

# Build with variables
packer build \
  -var 'azure_client_id=your-client-id' \
  -var 'azure_client_secret=your-client-secret' \
  -var 'azure_subscription_id=your-subscription-id' \
  -var 'azure_tenant_id=your-tenant-id' \
  -var 'azure_resource_group=packer-images' \
  -var 'sentinelgrid_agent_version=1.0.0' \
  ubuntu-22.04.json
```

### GCP Example (Ubuntu 22.04)

```bash
cd packer/ubuntu-22.04/gcp

# Build with variables
packer build \
  -var 'gcp_project_id=your-project-id' \
  -var 'gcp_account_file=path/to/service-account.json' \
  -var 'sentinelgrid_agent_version=1.0.0' \
  ubuntu-22.04.json
```

## Variables

### Common Variables

- `sentinelgrid_agent_version` - Agent version to install (default: "1.0.0")
- `sentinelgrid_tenant_token` - Tenant token for agent configuration (optional)
- `sentinelgrid_manager_host` - Manager hostname (default: "manager.sentinelgrid.ai")

### AWS Variables

- `aws_region` - AWS region (default: "us-east-1")
- `aws_instance_type` - Instance type for building (default: "t3.medium")
- `source_ami` - Source AMI ID
- `ssh_username` - SSH username (default: "ec2-user" or "ubuntu")

### Azure Variables

- `azure_client_id` - Azure service principal client ID
- `azure_client_secret` - Azure service principal client secret
- `azure_subscription_id` - Azure subscription ID
- `azure_tenant_id` - Azure tenant ID
- `azure_resource_group` - Resource group for images (default: "packer-images")
- `azure_location` - Azure location (default: "East US")
- `azure_vm_size` - VM size for building (default: "Standard_B2s")

### GCP Variables

- `gcp_project_id` - GCP project ID
- `gcp_account_file` - Path to service account JSON file
- `gcp_zone` - GCP zone (default: "us-east1-b")
- `gcp_machine_type` - Machine type for building (default: "n1-standard-2")

## What Gets Built

Each image includes:

1. **Base OS** - Latest stable version
2. **CIS Hardening** - Level 1 hardening applied
3. **SentinelGrid Agent** - Pre-installed and configured (if token provided)
4. **Security Updates** - All available security updates installed
5. **Cleanup** - SSH keys, history, and temporary files removed

## Image Tags/Labels

All images are tagged/labeled with:

- `Name` - Image name
- `OS` - Operating system
- `Hardening` - CIS Level 1
- `Agent` - SentinelGrid Endpoint Protection
- `ManagedBy` - Packer
- `Version` - Agent version

## Post-Build

After building, you can:

1. **Share Images** - Share AMIs/images with other accounts/subscriptions
2. **Launch Instances** - Launch instances from the hardened images
3. **Test** - Verify hardening and agent installation
4. **Distribute** - Make images available to customers

## Troubleshooting

### Build Fails

- Check cloud provider credentials
- Verify source image exists
- Check network connectivity
- Review Packer logs

### Agent Not Installed

- Verify CDN/repository is accessible
- Check agent version exists
- Review install script logs

### Hardening Issues

- Some settings may require manual adjustment
- SELinux/AppArmor may need permissive mode on first boot
- Review hardening script logs

## Automation

These templates can be integrated into CI/CD:

```yaml
# .github/workflows/build-images.yml
name: Build Hardened Images

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  build-aws:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: hashicorp/setup-packer@main
      - name: Build AMI
        run: |
          cd packer/amazon-linux-2/aws
          packer build amazon-linux-2.json
```

## Support

For issues or questions:
- Packer Documentation: https://www.packer.io/docs
- SentinelGrid Documentation: https://docs.sentinelgrid.ai

