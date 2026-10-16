# Agent Build Process

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document describes the step-by-step process for building and distributing SentinelGrid agents.

## Overview

SentinelGrid agents are rebranded versions of open-source security tools (primarily Wazuh). The build process includes:
1. Downloading upstream agents
2. Rebranding to SentinelGrid
3. Building packages
4. Uploading to CDN
5. Registering in database

## Prerequisites

- Access to upstream agent repositories
- Package build tools (rpmbuild, dpkg-deb)
- AWS CLI configured for CDN upload
- Database access for version registration
- GPG keys for package signing

## Build Steps

### 1. Download Agents

```bash
cd scripts/rebrand-agents
./download/download-wazuh.sh
```

This downloads Wazuh agents for all platforms:
- Linux RPM (RHEL/CentOS/Amazon Linux)
- Linux DEB (Debian/Ubuntu)
- Windows MSI
- macOS PKG

### 2. Extract Packages

```bash
./extract/extract-agents.sh
```

Extracts packages for rebranding.

### 3. Rebrand Agents

```bash
export WAZUH_VERSION=4.8.0
export SENTINELGRID_VERSION=1.0.0
./rebrand/rebrand-wazuh.sh
```

This:
- Replaces branding strings (Wazuh → SentinelGrid)
- Updates binary names
- Updates configuration files
- Adds attribution files

### 4. Build Packages

```bash
./build/build-packages.sh
```

Rebuilds packages with SentinelGrid branding.

### 5. Test Packages

```bash
./test/test-rebranded-agent.sh
```

Validates rebranded packages.

### 6. Upload to CDN

```bash
export SENTINELGRID_VERSION=1.0.0
export CDN_BUCKET=agents.sentinelgrid.ai
./upload/upload-to-cdn.sh
```

Uploads packages to S3/CDN for distribution.

### 7. Update Package Repositories

```bash
cd ../../package-repos
./update-repo-metadata.sh
./deploy-repos-to-cdn.sh
```

Updates APT and YUM repositories.

### 8. Register Version

Register the new version in the database:

```sql
INSERT INTO agent_versions (
    version, agent_type, upstream_tool, upstream_version,
    os_compatibility, package_urls, checksums, status, is_latest
) VALUES (
    '1.0.0',
    'endpoint',
    'wazuh',
    '4.8.0',
    '["amazon-linux-2", "ubuntu-22.04", "rhel-8", "debian-12"]'::jsonb,
    '{"rpm": "...", "deb": "...", "msi": "...", "pkg": "..."}'::jsonb,
    '{"rpm": "...", "deb": "...", "msi": "...", "pkg": "..."}'::jsonb,
    'stable',
    true
);
```

## Automation

The build process can be automated via CI/CD:

```yaml
# .github/workflows/rebrand-agents.yml
name: Rebrand Agents

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  rebrand:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Download Wazuh
        run: ./scripts/rebrand-agents/download/download-wazuh.sh
      - name: Rebrand
        run: ./scripts/rebrand-agents/rebrand/rebrand-wazuh.sh
      - name: Build
        run: ./scripts/rebrand-agents/build/build-packages.sh
      - name: Upload to CDN
        run: ./scripts/rebrand-agents/upload/upload-to-cdn.sh
```

## Version Management

### Bump Version

```bash
./scripts/version-management/bump-version.sh agent patch 1.0.0
# Output: 1.0.1
```

### Release Version

```bash
./scripts/version-management/release-version.sh agent 1.0.1
```

### Deprecate Version

```bash
./scripts/version-management/deprecate-version.sh agent 1.0.0 2025-12-31
```

## License Compliance

All rebranded packages must include:
1. Original license file (GPL v2 for Wazuh)
2. Attribution file (`SENTINELGRID_ATTRIBUTION.txt`)
3. Clear "Powered by Wazuh" attribution in UI
4. Source code modifications (if any) published

## Troubleshooting

### Build Fails

- Check package build tools are installed
- Verify extracted files are correct
- Review build logs

### Upload Fails

- Verify AWS credentials
- Check S3 bucket permissions
- Verify CDN configuration

### Version Registration Fails

- Check database connection
- Verify version format (semantic versioning)
- Check for duplicate versions

## Support

For issues or questions, contact the DevOps team.

