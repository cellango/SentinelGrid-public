# Customer Onboarding Guide – SAML & OIDC/OAuth (SentinelGuard IdP Gateway)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This guide shows how customers integrate their applications with SentinelGuard via our gateway. Keycloak stays private; all redirects/ACS go through our public gateway host.

## Endpoints (gateway)
- OIDC:
  - Authorize: `https://<your-auth-host>/auth/oidc/authorize?tenant_id=<TENANT_ID>`
  - Callback: `https://<your-auth-host>/auth/oidc/callback?tenant_id=<TENANT_ID>`
  - Logout: `https://<your-auth-host>/auth/oidc/logout?tenant_id=<TENANT_ID>`
- SAML:
  - Metadata: `https://<your-auth-host>/auth/saml/metadata?tenant_id=<TENANT_ID>`
  - ACS: `https://<your-auth-host>/auth/saml/acs?tenant_id=<TENANT_ID>`
  - SLO (if enabled): `https://<your-auth-host>/auth/saml/slo?tenant_id=<TENANT_ID>`

## Before you start
1) Obtain your `TENANT_ID` from your SentinelGuard admin.
2) Ensure your users’ email domains are listed in “Allowed domains” for your IdP connection (set in the SentinelGuard IAM portal).
3) Decide on roles:
   - Default role (optional) for all users of this IdP.
   - Group → role mappings (optional) to map IdP groups/claims to SentinelGuard roles.
   - Claim → attribute mappings (optional) to map custom claims/attributes to user fields.

## OIDC / OAuth2 (recommended)
1) In SentinelGuard (IAM → Identity Providers → Add OIDC), create an OIDC connection:
   - Discovery URL (https) from your app/IdP.
   - Client ID / Secret from your app.
   - Scopes (typically `openid email profile`).
   - Allowed domains; optional default role; claim/group mappings.
2) In your application (as an OIDC client):
   - Set the Issuer/Discovery URL to the one you provided.
   - Set Redirect URI to: `https://<your-auth-host>/auth/oidc/callback?tenant_id=<TENANT_ID>`
   - Set Logout URI (if supported) to: `https://<your-auth-host>/auth/oidc/logout?tenant_id=<TENANT_ID>`
   - Use the client ID/secret you created.
3) Test:
   - Use the “Test discovery” in the UI, then perform an interactive login.
   - On success, you should be redirected to the SentinelGuard app and see your assigned role.

## SAML 2.0
1) In SentinelGuard (IAM → Identity Providers → Add SAML), create a SAML connection:
   - Metadata URL (https) from your IdP.
   - Optional Authn Contexts; Allowed domains; default role; claim/group mappings.
2) In your IdP/app (as SAML SP settings):
   - ACS URL: `https://<your-auth-host>/auth/saml/acs?tenant_id=<TENANT_ID>`
   - EntityID: from the IdP metadata you configured (exposed via our Metadata URL above).
   - NameID: EmailAddress (recommended).
   - Sign assertions/responses; ensure the metadata uses https.
3) Test:
   - Use the “Test metadata” button in the UI.
   - Perform an SP-initiated login; verify redirect to SentinelGuard and role assignment.

## Roles & mappings (recommended defaults)
- Default role: use a minimal role (e.g., `user`) if you enable JIT provisioning.
- Group → role: map IdP groups (e.g., `Engineering`, `Security`) to SentinelGuard roles (`tenant_admin`, `analyst`, `viewer`).
- Claim → attribute: map `email`, `name`, `preferred_username` as needed.

## Domain enforcement & JIT
- Allowed domains are enforced at login; users outside the allowed domains are blocked.
- JIT provisioning should only be enabled after domain verification (TXT record or admin verification).

## Security checklist
- Always use https endpoints.
- Rotate client secrets regularly.
- For SAML, rotate signing certificates before expiry (dual-cert if supported).
- Use rate limiting/WAF on the gateway endpoints.

## Troubleshooting
- OIDC: check discovery URL, client ID/secret, scopes, and callback URI match exactly.
- SAML: ensure metadata is reachable via https, ACS URL matches exactly, and assertions are signed.
- If login fails with “Email domain not allowed”, update Allowed domains in the IdP configuration.
