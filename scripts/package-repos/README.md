# SentinelGrid Package Repositories

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains scripts and configurations for setting up package repositories for SentinelGrid agents.

## Supported Package Managers

1. **APT** (Debian/Ubuntu) - `apt/`
2. **YUM** (RHEL/CentOS/Amazon Linux) - `yum/`
3. **Homebrew** (macOS) - `homebrew/`
4. **Chocolatey** (Windows) - `chocolatey/`

## Quick Start

### APT Repository

```bash
cd scripts/package-repos/apt
./setup-apt-repo.sh
```

### YUM Repository

```bash
cd scripts/package-repos/yum
./setup-yum-repo.sh
```

### Homebrew Tap

```bash
cd scripts/package-repos/homebrew
./setup-homebrew-tap.sh
```

### Chocolatey Package

```bash
cd scripts/package-repos/chocolatey
./setup-chocolatey-package.sh
```

## Repository URLs

After setup, repositories are available at:

- **APT**: `https://agents.sentinelgrid.ai/apt/`
- **YUM**: `https://agents.sentinelgrid.ai/yum/`
- **Homebrew**: `brew tap sentinelgrid/agents`
- **Chocolatey**: `choco install sentinelgrid-agent`

## Maintenance

### Updating Packages

1. Add new packages to repository directory
2. Run update script:
   - APT: `apt-repo/update-repo.sh`
   - YUM: `yum-repo/update-repo.sh`
3. Upload to CDN
4. Update version manifest

### GPG Signing

All repositories support GPG signing for package verification:

```bash
# Generate GPG key
gpg --gen-key

# Export public key
gpg --armor --export <key-id> > gpg.key

# Upload to CDN
aws s3 cp gpg.key s3://agents.sentinelgrid.ai/apt/gpg.key
```

## Automation

Repository updates can be automated via CI/CD:

```yaml
# .github/workflows/update-repos.yml
name: Update Package Repositories

on:
  workflow_dispatch:
  schedule:
    - cron: '0 3 * * 0'  # Weekly

jobs:
  update-apt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Update APT repo
        run: ./scripts/package-repos/apt/update-repo.sh
      - name: Upload to CDN
        run: ./scripts/upload-repos-to-cdn.sh
```

