# SentinelGrid User Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Welcome to SentinelGrid! This guide will help you get started and make the most of your security monitoring platform.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Onboarding Wizard](#onboarding-wizard)
3. [Dashboard Overview](#dashboard-overview)
4. [Connecting Your Cloud](#connecting-your-cloud)
5. [Deploying Endpoint Protection](#deploying-endpoint-protection)
6. [Git Security Scanning](#git-security-scanning)
7. [Settings & Configuration](#settings--configuration)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Sign Up

1. Visit [SentinelGrid](https://sentinelgrid.ai)
2. Click "Get Started"
3. Fill in your account details:
   - Work email
   - Full name
   - Company name
   - Company domain
   - Password
4. Select your company size and primary cloud provider
5. Complete payment
6. You'll be redirected to the dashboard

### First Login

After signing up, you'll see the onboarding wizard. This guides you through:
1. Connecting your identity provider
2. Connecting your cloud accounts
3. Deploying endpoint protection
4. Connecting Git repositories

You can skip any step and complete it later from Settings.

---

## Onboarding Wizard

### Step 1: Connect Identity Provider

Choose how you want to manage user authentication:

**Options:**
- **Google Workspace** - OAuth integration (recommended)
- **Microsoft 365 / Entra ID** - OAuth integration
- **Okta** - API token configuration
- **Keycloak** - Self-hosted configuration
- **SentinelGrid Identity** - Use our built-in IdP (default)

**To Connect:**
1. Select your IdP
2. Follow the on-screen instructions
3. Click "Continue"

**Note:** You can always change this later in Settings.

---

### Step 2: Connect Your Cloud

Connect your cloud accounts to start monitoring:

**Supported Providers:**
- **AWS** - Account ID and IAM Role ARN
- **Azure** - Tenant ID, Client ID, Client Secret, Subscription ID
- **GCP** - Project ID and Service Account JSON

**AWS Setup:**
1. We'll generate an External ID for you
2. Use our Terraform module or CloudFormation template
3. Deploy in your AWS account
4. Paste the IAM Role ARN

**Azure Setup:**
1. Create an Azure AD application
2. Assign required roles (Reader, Security Reader)
3. Enter Tenant ID, Client ID, Client Secret, Subscription ID

**GCP Setup:**
1. Create a service account
2. Grant required permissions
3. Download service account key
4. Paste the JSON key

**After Connection:**
- CloudTrail/Activity logs will start ingesting
- Security findings will appear within a few hours
- You'll see your first insights on the dashboard

---

### Step 3: Deploy Endpoint Protection

Choose how to protect your endpoints:

**Option 1: Hardened Images (Recommended)**
- Pre-hardened OS images with SentinelGrid agent pre-installed
- CIS Level 1 compliance
- Available for AWS, Azure, GCP
- Select your OS (Amazon Linux, Ubuntu, RHEL, etc.)

**Option 2: Manual Installation**
- Install agent on existing servers
- Follow installation instructions
- Supports Linux, Windows, macOS

**To Deploy:**
1. Select a hardened image or choose manual installation
2. Launch instances from the image (or install manually)
3. Agents will auto-register with your tenant
4. You'll see agents appear on the dashboard

---

### Step 4: Connect Git Repositories

Connect your Git repositories for security scanning:

**Supported Providers:**
- **GitHub** - Personal Access Token
- **GitLab** - Personal Access Token (supports self-hosted)
- **Bitbucket** - App Password
- **Azure DevOps** - Personal Access Token

**To Connect:**
1. Select your Git provider
2. Create an access token with `repo` scope
3. Enter the token
4. Optionally specify organization/workspace
5. Click "Connect"

**After Connection:**
- Repositories will be synced
- You can trigger security scans
- Findings will appear in Git Security section

---

## Dashboard Overview

### Onboarding Banner

If onboarding is incomplete, you'll see a banner at the top:
- Shows progress (X of 4 steps completed)
- Lists missing steps
- "Continue Setup" button takes you to the next step

### Integration Status Cards

**Cloud Connections:**
- Shows connected cloud accounts
- Status indicators (Connected/Error/Testing)
- Last sync timestamps
- "Connect" or "Manage" button

**Endpoint Agents:**
- Total, Online, Offline, Error counts
- Agent list with hostname, type, version
- Status indicators
- "Deploy" or "Manage" button

**Git Security:**
- Findings summary (Total, Critical, High, Medium, Low)
- Recent findings list
- "Connect" or "View All" button

### Security Overview

**Metrics:**
- Active Alerts
- Incidents
- Findings

### Recent Alerts & Incidents

Lists the most recent security events:
- Alert/Incident title
- Severity (Critical, High, Medium, Low)
- Status
- Detection time

---

## Connecting Your Cloud

### AWS

**Prerequisites:**
- AWS Account ID
- Terraform or CloudFormation access

**Steps:**
1. Go to Settings → Cloud Accounts
2. Click "Add Cloud Account" → AWS
3. Enter your AWS Account ID
4. We'll generate an External ID
5. Download our Terraform module or CloudFormation template
6. Deploy in your AWS account
7. Paste the IAM Role ARN
8. Click "Connect"

**Required Permissions:**
- CloudTrail read access
- GuardDuty read access
- Config read access
- Security Hub read access
- S3 read access (for CloudTrail logs)

### Azure

**Prerequisites:**
- Azure subscription
- Azure AD admin access

**Steps:**
1. Go to Settings → Cloud Accounts
2. Click "Add Cloud Account" → Azure
3. Create Azure AD application:
   - Go to Azure Portal → App registrations
   - Create new registration
   - Generate client secret
4. Assign roles:
   - Reader
   - Security Reader
   - Log Analytics Reader
   - Monitoring Reader
5. Enter Tenant ID, Client ID, Client Secret, Subscription ID
6. Click "Connect"

### GCP

**Prerequisites:**
- GCP project
- Service account creation access

**Steps:**
1. Go to Settings → Cloud Accounts
2. Click "Add Cloud Account" → GCP
3. Create service account:
   - Go to GCP Console → IAM & Admin → Service Accounts
   - Create service account
   - Grant roles: Viewer, Security Reviewer, etc.
   - Create and download JSON key
4. Enter Project ID and paste service account JSON
5. Click "Connect"

---

## Deploying Endpoint Protection

### Using Hardened Images

**AWS:**
1. Go to Onboarding → Step 3 or Settings → Agents
2. Select cloud provider: AWS
3. Choose OS (Amazon Linux, Ubuntu, etc.)
4. Select region
5. Click on an image to see details
6. Launch instance from the image
7. Agent will auto-register

**Azure:**
1. Select cloud provider: Azure
2. Choose OS
3. Select subscription and region
4. Launch VM from the image
5. Agent will auto-register

**GCP:**
1. Select cloud provider: GCP
2. Choose OS
3. Select project and region
4. Launch VM from the image
5. Agent will auto-register

### Manual Installation

**Linux:**
```bash
curl -sSL https://agents.sentinelgrid.ai/install.sh | bash
```

**Windows:**
```powershell
Invoke-WebRequest -Uri "https://agents.sentinelgrid.ai/install.ps1" -OutFile install.ps1
.\install.ps1
```

**macOS:**
```bash
brew install sentinelgrid-agent
```

---

## Git Security Scanning

### Connecting a Repository

1. Go to Settings → Git Security
2. Click "Connect Git Provider"
3. Select provider (GitHub, GitLab, etc.)
4. Enter access token
5. Click "Connect"

### Running a Scan

1. Go to Git Security section
2. Select a repository
3. Click "Scan Now"
4. Choose scan types:
   - Secrets (Gitleaks)
   - Dependencies (Trivy)
   - Code Issues (Semgrep)
5. Wait for scan to complete
6. Review findings

### Viewing Findings

**Filters:**
- Severity (Critical, High, Medium, Low)
- Finding Type (Secret, Vulnerability, Code Issue)
- Status (Open, Resolved, False Positive, Ignored)

**Actions:**
- View details
- Mark as resolved
- Mark as false positive
- Ignore

---

## Settings & Configuration

### Profile Settings

Update your profile:
- Email (read-only)
- Full Name
- Company

### Identity Provider

Change your IdP connection:
- Disconnect current IdP
- Connect new IdP
- Use SentinelGrid Identity

### Cloud Accounts

Manage cloud connections:
- View connected accounts
- Add new accounts
- Remove accounts
- Test connections

### Agents

Manage endpoint agents:
- View all agents
- Agent status
- Deployment instructions
- Agent versions

### Git Security

Manage Git providers:
- View connected providers
- Add new providers
- Sync repositories
- View scan history

---

## Troubleshooting

### Cloud Connection Issues

**AWS:**
- Verify IAM role exists
- Check External ID matches
- Verify role has required permissions
- Check CloudTrail is enabled

**Azure:**
- Verify service principal exists
- Check roles are assigned
- Verify client secret is valid
- Check subscription is active

**GCP:**
- Verify service account exists
- Check IAM roles are granted
- Verify JSON key is valid
- Check project is active

### Agent Issues

**Agent Not Appearing:**
- Check agent is installed
- Verify network connectivity
- Check agent registration token
- Review agent logs

**Agent Offline:**
- Check agent service is running
- Verify network connectivity
- Check firewall rules
- Review agent logs

### Git Scanning Issues

**Scan Not Starting:**
- Verify repository access
- Check scan queue
- Review scan logs

**No Findings:**
- Verify scan completed
- Check scan types selected
- Review repository content

---

## Support

**Documentation:** [docs.sentinelgrid.ai](https://docs.sentinelgrid.ai)  
**Support Email:** support@sentinelgrid.ai  
**Community:** [community.sentinelgrid.ai](https://community.sentinelgrid.ai)

---

**Last Updated:** 2025-11-30

