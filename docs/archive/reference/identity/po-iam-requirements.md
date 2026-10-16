
> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.

IAM Platform Requirements for Small Businesses (1–50 Users)
This document outlines key product requirements for building a lightweight yet secure Identity & Access Management (IAM) platform tailored for small businesses. The focus is on simplicity, affordability, low maintenance, and strong security features.

 
1. Core Identity Management Requirements
1.1 User Lifecycle Management
Create, read, update, delete (CRUD) operations for user accounts
Simple onboarding/offboarding wizard
Bulk user upload via CSV
Invite-based onboarding for contractors or temporary users
Basic user profile attributes (name, email, phone, role, department)
1.2 Authentication
Password-based authentication with configurable policies
Support for passwordless (magic link, OTP)
TOTP MFA (Google Authenticator, Authy)
Backup codes for account recovery
Hardware key support (WebAuthn/FIDO2) – optional but recommended
1.3 Authorization
Basic role-based access control (RBAC)
Predefined roles for common small-business apps (admin, manager, staff)
Resource access policies for apps connected through the IAM
Fine-grained permissions for files, apps, and infrastructure components
 
2. Directory & Identity Store
Lightweight cloud directory (your own or built on open directory tech)
SCIM 2.0 support for provisioning/deprovisioning
Simple group management
Local directory sync option for small Windows/AD-based shops
 
3. Single Sign-On (SSO)
3.1 Protocol Support
SAML 2.0
OAuth 2.0
OpenID Connect
3.2 App Catalog
Prebuilt SSO integrations for:
Microsoft 365
Google Workspace
QuickBooks Online
Slack
Zoom
Dropbox
Salesforce (optional)
GitHub / GitLab
Custom app connector wizard
 
4. Multi-Factor Authentication (MFA)
Enforce MFA per user, per role, per app
Policy-based MFA challenges
Context-aware MFA (device, IP, geo, time)
Push notifications (optional v2 feature)
 
5. Device & Endpoint Security Requirements
5.1 Device Inventory
Track registered devices (PC, Mac, mobile)
OS version and security posture (optional through agent or integration)
5.2 Lightweight Agent (Optional Phase)
Enforce screen lock
Enforce disk encryption (Windows BitLocker, macOS FileVault)
Notify admin when a device is insecure or compromised
5.3 Mobile Device Management (MDM-lite)
Basic controls: enforce passcode, remote wipe for lost devices
API integration with iOS/Android MDM frameworks
 
6. Infrastructure Protection Features
6.1 Zero Trust Network Access (ZTNA-lite)
Secure access to internal applications without VPN
Device posture check before granting access
6.2 Secrets & Key Management
Simple password vault for shared credentials
Secure storage for API keys (hashed + encrypted)
Rotation of shared secrets
6.3 Privileged Access Controls
Just‑in‑time (JIT) access for admins
Approval workflows for elevated access
Session recording for SSH/RDP (optional advanced feature)
6.4 API Gateway Security
Protect access to small business APIs exposed to internet
Rate limiting, API keys, token-based authorization
 
7. Threat Protection Features
7.1 Anomaly Detection
Impossible travel, unusual geo, unusual device
Multiple failed login attempts
Suspicious MFA push fatigue detection
7.2 Basic SIEM/Lite Logging
Cloud audit logs (auth events, MFA events, policy changes)
Integrations with Wazuh, OpenSearch, ELK, and security dashboards
7.3 Automated Response
Temporarily lock suspicious accounts
Force MFA after high‑risk events
Send admin alerts via email/SMS/mobile
 
8. Admin & Policy Management
8.1 Dashboard
User metrics (active, inactive, MFA coverage)
Failed logins, anomalies, device security summary
8.2 Policy Controls
Password strength requirements
MFA enforcement rules
App access policies
Device trust rules
8.3 Reporting
Compliance reports (login history, MFA adoption, access logs)
Export to PDF/CSV
 
9. Self‑Service for End Users
Reset password with MFA
Update profile and devices
View access to apps and request new access
QR code‑based enrollment
 
10. Architecture Requirements
Multi-tenant by design
Lightweight onboarding (5-minute setup)
Simple pricing (per user per month)
Low compute footprint to keep costs low
Optional on‑prem connector for legacy integration
 
11. Data Protection & Compliance
Strong encryption at rest and in transit
Logging of all administrator actions
Data residency options (US, EU optional)
Compliance templates (SOC2-ready architecture)
 
12. Support & Customer Experience
Guided onboarding wizard
Prebuilt templates for policies
24/7 chat support or AI-driven assistant
Knowledge base + how-to videos
 
13. Pricing Model (Recommended)
Free tier: up to 3 users, basic SSO + MFA
Standard: $3–$5/user/month (full IAM)
Premium: $8–$12/user/month (ZTNA + device trust + threat intel)
 
14. Roadmap Suggestions (High-Level)
Phase 1 (MVP)
IAM + MFA + SSO + audit logs + small app catalog
Phase 2
Basic anomaly detection + password vault + SCIM provisioning
Phase 3
Device trust, ZTNA-lite, app connectors, automated remediation
Phase 4
Full contextual MFA + agent posture checks + privilege workflows
 
