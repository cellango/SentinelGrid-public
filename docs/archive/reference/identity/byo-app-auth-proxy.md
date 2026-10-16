# Bring Your Own App (No SSO Yet) — Auth Proxy Quickstart

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Goal: let customers front any homegrown app (no SAML/OIDC) with an auth proxy so it gets SSO in minutes. Minimal effort: drop in a proxy, trust headers, stay tenant-aware.

## What we provide
- **Tenant-aware config** (per app, per tenant): Keycloak issuer/discovery URL, client ID/secret, redirect/callback.
- **One-click download** (planned UI): in People & Access → Applications → “Add App (No SSO yet)” → generate client + download proxy config.
- **Header contract** (what the app should read): `X-User`, `X-Email`, `X-Groups`, `X-Roles`. Apps trust only headers injected by the proxy.
- **Zero/low-friction templates**: docker-compose snippet and NGINX/Ingress annotations that work with the tenant’s realm.

## Recommended proxy options
1) **oauth2-proxy** (simplest, self-contained reverse proxy)
2) **NGINX/Traefik auth_request** (ingress-friendly; calls an OIDC verifier endpoint)

Both terminate OIDC, validate tokens, and inject headers before forwarding to your app.

## Inputs per tenant/app
- Issuer/Discovery: `https://<host>/realms/<tenant>`
- Client ID / Secret: from the “BYO App” entry (tenant-scoped client in Keycloak)
- Redirect/Callback: e.g., `https://app.example.com/oauth2/callback`
- Upstream (your app): e.g., `http://your-app:8080`

## Quickstart: oauth2-proxy (docker-compose)
```yaml
version: "3"
services:
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
    ports: ["4180:4180"]
    environment:
      OAUTH2_PROXY_PROVIDER: "oidc"
      OAUTH2_PROXY_OIDC_ISSUER_URL: "https://<host>/realms/<tenant>"
      OAUTH2_PROXY_CLIENT_ID: "<client-id>"
      OAUTH2_PROXY_CLIENT_SECRET: "<client-secret>"
      OAUTH2_PROXY_REDIRECT_URL: "https://app.example.com/oauth2/callback"
      OAUTH2_PROXY_UPSTREAMS: "http://your-app:8080"
      OAUTH2_PROXY_EMAIL_DOMAINS: "*"
      OAUTH2_PROXY_COOKIE_SECURE: "true"
      OAUTH2_PROXY_SET_XAUTHREQUEST: "true"
      OAUTH2_PROXY_PASS_AUTHORIZATION_HEADER: "true"
    # Optional TLS termination in front (nginx/ingress); otherwise add certificates here.
```
Your app reads headers:
- `X-Forwarded-User` / `X-User`
- `X-Forwarded-Email` / `X-Email`
- `X-Auth-Request-Groups` / `X-Groups`
- `X-Auth-Request-Roles` / `X-Roles`

## Quickstart: NGINX ingress (k8s) with auth_request
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: your-app
  annotations:
    nginx.ingress.kubernetes.io/auth-url: "https://authproxy.your-domain.com/oauth2/auth"
    nginx.ingress.kubernetes.io/auth-signin: "https://authproxy.your-domain.com/oauth2/start?rd=$request_uri"
    nginx.ingress.kubernetes.io/auth-response-headers: "Authorization,X-User,X-Email,X-Groups,X-Roles"
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: your-app-svc
            port:
              number: 8080
```
Deploy oauth2-proxy alongside and point `auth-url`/`auth-signin` to it. NGINX forwards headers to your app.

## Security guardrails (baked into templates)
- HTTPS only (allow `localhost` for dev).
- Short token TTLs; rely on JWKS from your realm; modest cache.
- Do not trust incoming auth headers unless set by the proxy.
- Enforce allowed redirect/callback URLs per app.
- MFA/privileged role enforcement can be added later via policy.

## Operational notes
- **Multi-tenant**: each BYO app creates a Keycloak client in that tenant’s realm; configs are tenant-scoped.
- **Activation**: keep app in Draft until redirect is set; show “Needs Attention” badge if missing redirect/assignments.
- **Debugging**: oauth2-proxy `/oauth2/userinfo` and logs; check JWKS reachability; ensure clock sync.

## Roadmap (future)
- “Download config” button wired to the app detail page.
- Optional SentinelGrid-branded thin proxy (Go) after hardening; oauth2-proxy remains supported.
- Prebaked Helm chart/values for k8s users.
```
