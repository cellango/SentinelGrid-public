# SentinelGrid IAM Administrator Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Date:** 2025-01-28  
**Audience:** Administrators

---

## Table of Contents

1. [Overview](#overview)
2. [User Management](#user-management)
3. [Application Management](#application-management)
4. [Security Policies](#security-policies)
5. [Device Management](#device-management)
6. [Threat Protection](#threat-protection)
7. [Reporting & Compliance](#reporting--compliance)
8. [Advanced Features](#advanced-features)

---

## Overview

SentinelGrid IAM provides comprehensive identity and access management for your organization. This guide covers administrative tasks and best practices.

### Key Features

- **User Lifecycle Management**: Invite, onboard, and offboard users
- **Single Sign-On (SSO)**: Connect applications for seamless access
- **Multi-Factor Authentication**: Enforce MFA policies
- **Device Security**: Track and manage registered devices
- **Threat Detection**: Automated anomaly detection and response
- **Compliance Reporting**: Generate audit reports

---

## User Management

### Inviting Users

1. Go to **IAM** → **People**
2. Click **Add User**
3. Enter work email, optional first/last name, and **tenant** (required)
4. Set **Department** and **Team** (optional but recommended for filtering/reporting)
5. Select access profile or admin flag (if applicable)
6. Click **Send Invitation**

The user will receive an email with setup instructions.

### Bulk User Import

1. Go to **IAM** → **People**
2. Click **Add User** → **Bulk Upload**
3. Prepare CSV file with columns: `email,firstName,lastName,role,enabled`
4. Upload the CSV file
5. Review import results

**CSV Format:**
```csv
email,firstName,lastName,role,enabled
user1@example.com,John,Doe,SOC_ANALYST,true
user2@example.com,Jane,Smith,VIEW_ONLY,true
```

### User Offboarding

1. Go to **IAM** → **People**
2. Find the user
3. Click **Offboard**
4. Review offboarding checklist:
   - Disable account
   - Revoke all sessions
   - Transfer resource ownership (if needed)
5. Confirm offboarding

### Managing User Roles

1. Go to **IAM** → **People**
2. Select a user
3. Click **Edit**
4. Assign roles from available list
5. Update Department/Team if needed
6. Save changes

**Available Roles:**
- **TENANT_ADMIN**: Full administrative access
- **SOC_MANAGER**: Security operations management
- **SOC_ANALYST**: Security analyst access
- **VIEW_ONLY**: Read-only access

---

## Application Management

### Prebuilt App Catalog

1. Go to **IAM** → **Apps** → **Catalog**
2. Browse available applications:
   - Microsoft 365
   - Google Workspace
   - Slack
   - Zoom
   - GitHub
   - And more...
3. Click **Connect** on an app
4. Follow the setup wizard:
   - Enter SSO configuration details
   - Configure access control
   - Review and create

### Custom App Setup

1. Go to **IAM** → **Apps**
2. Click **Add Application**
3. Choose app type:
   - **Internal Web App**: Internal applications
   - **External SaaS**: Third-party SaaS applications
   - **VPN/RADIUS**: Network access
4. Configure:
   - Name and description
   - SSO protocol (SAML, OIDC)
   - Redirect URLs
   - Access control (all users or specific groups)
5. Save configuration

### External Identity Providers

#### Connect Microsoft 365

1. Go to **IAM** → **Identity Providers**
2. Click **Connect Microsoft 365**
3. Enter Azure AD details:
   - Tenant ID
   - Client ID
   - Client Secret
4. Configure user/group sync
5. Save

#### Connect Google Workspace

1. Go to **IAM** → **Identity Providers**
2. Click **Connect Google Workspace**
3. Enter OAuth credentials:
   - Domain
   - Client ID
   - Client Secret
4. Configure sync options
5. Save

---

## Security Policies

### MFA Policies

1. Go to **IAM** → **Policies**
2. Select **MFA Policy**
3. Configure:
   - **Enforcement**: Require MFA for all users or specific roles
   - **Context-aware**: Require MFA based on risk
   - **Device trust**: Skip MFA for trusted devices
4. Save policy

### Access Policies

1. Go to **IAM** → **Policies**
2. Select **Access Policy**
3. Configure:
   - **Time-based**: Restrict access to business hours
   - **Location-based**: Restrict access by IP/geo-location
   - **Device-based**: Require trusted devices
4. Save policy

### Sign-On Policies

1. Go to **IAM** → **Policies**
2. Select **Sign-On Policy**
3. Configure:
   - **Password requirements**: Complexity, expiration
   - **Session duration**: Maximum session time
   - **Concurrent sessions**: Limit simultaneous logins
4. Save policy

---

## Device Management

### Viewing Device Inventory

1. Go to **IAM** → **Devices**
2. View all registered devices:
   - Device name and type
   - Operating system
   - Trust status
   - Last seen timestamp
3. Filter by:
   - Trust status
   - Device type
   - User

### Managing Device Trust

1. Go to **IAM** → **Devices**
2. Select a device
3. Click **Set Trust Status**
4. Choose:
   - **Trusted**: Device is known and secure
   - **Untrusted**: Device requires additional verification
   - **Revoked**: Device access is blocked
5. Add reason (optional)
6. Save

### Device Policies

1. Go to **IAM** → **Devices**
2. Click **Device Policies**
3. Create policy:
   - **Name**: Policy name
   - **Rules**: Compliance requirements
   - **Enforcement**: Automatic or manual
4. Assign to devices or users

### Remote Wipe

**Warning**: This will erase data on the device.

1. Go to **IAM** → **Devices**
2. Select a lost/stolen device
3. Click **Remote Wipe**
4. Confirm action
5. Device will be wiped on next connection

---

## Threat Protection

### Security Events Dashboard

1. Go to **IAM** → **Security Events**
2. View detected anomalies:
   - **Impossible travel**: Login from distant locations
   - **Unusual device**: New or untrusted device
   - **Failed logins**: Multiple failed attempts
   - **MFA fatigue**: Excessive MFA requests
3. Filter by:
   - Date range
   - Event type
   - Severity
4. **Acknowledge** events after review

### Automated Responses

Configure automated responses to security threats:

1. Go to **IAM** → **Policies** → **Security Policies**
2. Configure response rules:
   - **High risk**: Auto-lock account
   - **Medium risk**: Force MFA
   - **All risks**: Send admin alert
3. Save policy

### Anomaly Detection

1. Go to **IAM** → **Security Events**
2. Click **Detect Anomalies** (manual trigger)
3. Review detected anomalies
4. Take appropriate action:
   - Acknowledge (false positive)
   - Investigate further
   - Take remediation action

---

## Reporting & Compliance

### Generating Reports

1. Go to **IAM** → **Reports**
2. Select report type:
   - **Login History**: User authentication events
   - **MFA Adoption**: MFA enrollment statistics
   - **Access Logs**: Resource access activity
3. Configure:
   - Date range
   - Format (CSV or PDF)
4. Click **Generate Report**
5. Download report

### Dashboard Metrics

View key metrics on the IAM dashboard:

- **User counts**: Total, active, inactive, admins, by tenant
- **MFA coverage**: Percentage of users with MFA
- **Failed logins**: Last 24 hours
- **Anomalies**: Total and critical count
- **Device security**: Trusted vs untrusted devices
- **Fast wins**: Recommended security improvements

---

## Advanced Features

### Privileged Access (JIT)

Manage just-in-time privileged access:

1. Go to **IAM** → **Privileged Access**
2. **Request Access**:
   - Select resource (role, permission, resource)
   - Provide reason (required)
   - Set duration (1-24 hours)
   - Submit request
3. **Approve Requests**:
   - Review pending requests
   - Approve or reject with reason
   - Access is automatically granted/revoked
4. **Revoke Access**: Manually revoke before expiration

### Secrets Vault

Manage shared credentials:

1. Go to **IAM** → **Secrets**
2. **Add Secret**:
   - Name and description
   - Secret type (password, API key, token, certificate)
   - Value (encrypted)
   - Rotation schedule (optional)
3. **Rotate Secret**: Generate new value
4. **Delete Secret**: Remove when no longer needed

### API Keys

Manage API keys for programmatic access:

1. Go to **IAM** → **API Keys**
2. **Create API Key**:
   - Name
   - Scopes/permissions
   - Rate limits
   - Expiration (optional)
3. **Copy key immediately** (shown only once)
4. **Rotate Key**: Generate new key, invalidate old
5. **Revoke Key**: Disable access

### ZTNA (Zero Trust Network Access)

Provide secure access to internal apps:

1. Go to **IAM** → **Apps**
2. Enable ZTNA for internal applications
3. Configure device posture requirements
4. Users can access apps without VPN
5. Device compliance is checked before access

---

## Best Practices

### User Management

- **Regular audits**: Review user access quarterly
- **Offboard promptly**: Disable accounts immediately when users leave
- **Principle of least privilege**: Grant minimum necessary access
- **Role-based access**: Use roles instead of individual permissions

### Security

- **Enforce MFA**: Require MFA for all users, especially admins
- **Monitor anomalies**: Review security events regularly
- **Device trust**: Only trust known, secure devices
- **Password policies**: Enforce strong password requirements

### Applications

- **SSO everywhere**: Connect all applications for better security
- **Regular reviews**: Audit application access quarterly
- **Remove unused apps**: Disconnect applications no longer in use

### Compliance

- **Regular reports**: Generate compliance reports monthly
- **Audit logs**: Review access logs for suspicious activity
- **Documentation**: Keep records of access changes

---

## Troubleshooting

### Users Can't Sign In

- Check account status (enabled/disabled)
- Verify email is correct
- Check for account lockouts
- Review MFA status

### SSO Not Working

- Verify app configuration (redirect URLs, entity ID)
- Check Keycloak client configuration
- Review user access permissions
- Check application logs

### Device Issues

- Verify device is registered
- Check device trust status
- Review device security posture
- Check endpoint protection integration

### Anomaly False Positives

- Acknowledge false positives
- Adjust detection thresholds
- Whitist trusted IPs/locations
- Review and tune policies

---

## Getting Help

- **Documentation**: Check user and developer guides
- **Support**: Contact SentinelGrid support team
- **Security incidents**: Report immediately to security team

---

**Last Updated:** 2025-01-28
