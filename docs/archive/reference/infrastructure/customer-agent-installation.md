# Customer Agent Installation Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This guide explains how customers can install SentinelGrid agents on their systems.

## Overview

SentinelGrid agents are available for multiple platforms and can be installed via:
- Package repositories (APT, YUM)
- Direct download from CDN
- Installation scripts

## Supported Platforms

- **Linux**: Amazon Linux 2, Ubuntu 22.04, RHEL 8, Debian 12
- **Windows**: Windows Server 2019, 2022
- **macOS**: macOS 10.15+

## Installation Methods

### Method 1: Package Repository (Recommended)

#### APT (Debian/Ubuntu)

```bash
# Import GPG key
curl -fsSL https://agents.sentinelgrid.ai/apt/gpg.key | sudo apt-key add -

# Add repository
echo "deb [arch=amd64] https://agents.sentinelgrid.ai/apt stable main" | sudo tee /etc/apt/sources.list.d/sentinelgrid.list

# Update package list
sudo apt-get update

# Install agent
sudo apt-get install sentinelgrid-agent
```

#### YUM (RHEL/CentOS/Amazon Linux)

```bash
# Import GPG key
sudo rpm --import https://agents.sentinelgrid.ai/yum/RPM-GPG-KEY-sentinelgrid

# Add repository
sudo curl -o /etc/yum.repos.d/sentinelgrid.repo https://agents.sentinelgrid.ai/yum/sentinelgrid.repo

# Install agent
sudo yum install sentinelgrid-agent
# or for newer systems:
sudo dnf install sentinelgrid-agent
```

### Method 2: Direct Download

Download the appropriate package for your platform from:
- **API**: `GET /api/v1/agents/versions/latest`
- **CDN**: `https://agents.sentinelgrid.ai/v{version}/{platform}/`

### Method 3: Installation Script

Use the installation script endpoint:
```bash
curl https://api.sentinelgrid.ai/api/v1/agents/install/linux_rpm | bash
```

## Configuration

After installation, configure the agent with your tenant token:

```bash
# Linux
sudo /var/ossec/bin/agent-auth -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN

# Windows
"C:\Program Files (x86)\ossec-agent\agent-auth.exe" -m manager.sentinelgrid.ai -A YOUR_TENANT_TOKEN
```

## Start Service

```bash
# Linux
sudo systemctl enable sentinelgrid-agent
sudo systemctl start sentinelgrid-agent

# Windows
# Service starts automatically after installation
```

## Verify Installation

```bash
# Linux
sudo systemctl status sentinelgrid-agent

# Check agent logs
sudo tail -f /var/ossec/logs/ossec.log
```

## Updating Agents

### APT
```bash
sudo apt-get update
sudo apt-get upgrade sentinelgrid-agent
```

### YUM
```bash
sudo yum update sentinelgrid-agent
# or
sudo dnf update sentinelgrid-agent
```

## Troubleshooting

### Agent Not Connecting

1. Verify tenant token is correct
2. Check network connectivity to `manager.sentinelgrid.ai`
3. Verify firewall rules allow outbound connections
4. Check agent logs for errors

### Service Not Starting

1. Check service status: `sudo systemctl status sentinelgrid-agent`
2. Review logs: `sudo journalctl -u sentinelgrid-agent`
3. Verify configuration: `/var/ossec/etc/ossec.conf`

## Support

For issues or questions:
- Email: support@sentinelgrid.ai
- Documentation: https://docs.sentinelgrid.ai
- API: https://api.sentinelgrid.ai/api/v1/agents/versions

