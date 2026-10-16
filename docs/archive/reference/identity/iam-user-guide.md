# SentinelGrid IAM User Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Date:** 2025-01-28  
**Audience:** End Users

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [My Account Portal](#my-account-portal)
3. [Authentication](#authentication)
4. [Accessing Applications](#accessing-applications)
5. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Login

1. You will receive an invitation email from your administrator
2. Click the link in the email to set up your account
3. Create a strong password (minimum 8 characters)
4. Complete your profile information
5. Set up multi-factor authentication (MFA) for added security

### Setting Up MFA

1. Go to **My Account** → **Security**
2. Click **Set Up MFA**
3. Scan the QR code with an authenticator app (Google Authenticator, Authy, etc.)
4. Enter the 6-digit code to verify
5. Save your backup codes in a secure location

---

## My Account Portal

Access your account settings from the header menu or navigate to **IAM** → **My Account**.

### Profile Tab

- **Update your name**: Edit first and last name
- **Change timezone**: Set your preferred timezone
- **Change language**: Select your preferred language
- **Email**: Your email cannot be changed (contact admin if needed)

### Security Tab

#### Change Password

1. Click **Change Password**
2. Enter your current password
3. Enter your new password (minimum 8 characters)
4. Click **Change Password**

#### Manage MFA

- **View MFA status**: See if MFA is enabled
- **Remove MFA**: Disable multi-factor authentication
- **Generate backup codes**: Create new backup codes if lost

#### Active Sessions

- **View active sessions**: See all devices where you're logged in
- **Sign out from device**: Remotely log out from a specific device
- **IP address**: See the IP address of each session
- **Last access**: See when each session was last active

### Apps Tab

- **App Launcher**: View all applications you have access to
- **SSO Access**: Click any app to sign in automatically
- **App descriptions**: See what each application is for

### Access Tab

- **View entitlements**: See what permissions and roles you have
- **Access profiles**: View your assigned access profile
- **Resource access**: See what resources you can access

---

## Authentication

### Password-Based Login

1. Enter your email address
2. Enter your password
3. If MFA is enabled, enter the 6-digit code from your authenticator app
4. Click **Sign In**

### Passwordless Login

#### Magic Link

1. Click **Sign in with magic link**
2. Enter your email address
3. Check your email for the magic link
4. Click the link to sign in (no password needed)

#### One-Time Password (OTP)

1. Click **Sign in with OTP**
2. Enter your email address
3. Check your email for the 6-digit code
4. Enter the code to sign in

### WebAuthn (Security Keys)

1. Go to **My Account** → **Security**
2. Click **Register Security Key**
3. Follow the browser prompts to register your hardware key (YubiKey, etc.)
4. Use your security key for passwordless login

---

## Accessing Applications

### Single Sign-On (SSO)

1. Go to **My Account** → **Apps**
2. Click on any application
3. You'll be automatically signed in (no password needed)

### App Catalog

If your administrator has enabled the app catalog:

1. Go to **IAM** → **Apps** → **Catalog**
2. Browse available applications
3. Request access to new apps (if allowed)

---

## Troubleshooting

### Can't Sign In

- **Forgot password**: Click "Forgot password" and check your email
- **Account locked**: Contact your administrator
- **MFA code not working**: 
  - Check that your device time is correct
  - Use a backup code if available
  - Contact administrator to reset MFA

### Can't Access an Application

- **Check permissions**: Verify you have access to the app
- **Contact administrator**: Request access if needed
- **Check SSO configuration**: App may not be properly configured

### Session Issues

- **Too many sessions**: Sign out from old devices in **My Account** → **Security** → **Active Sessions**
- **Session expired**: Sign in again
- **Device not trusted**: Register your device or contact administrator

### MFA Issues

- **Lost authenticator device**: Use backup codes or contact administrator
- **Backup codes used**: Generate new codes in **My Account** → **Security**
- **QR code not working**: Try manual entry key instead

---

## Security Best Practices

1. **Use strong passwords**: Minimum 8 characters, mix of letters, numbers, and symbols
2. **Enable MFA**: Always use multi-factor authentication when available
3. **Review active sessions**: Regularly check and sign out from unused devices
4. **Keep backup codes safe**: Store backup codes in a secure password manager
5. **Report suspicious activity**: Contact your administrator immediately if you notice anything unusual

---

## Getting Help

- **Contact your administrator**: For account issues or access requests
- **Check documentation**: Visit the admin documentation for more details
- **Security incidents**: Report immediately to your security team

---

**Last Updated:** 2025-01-28

