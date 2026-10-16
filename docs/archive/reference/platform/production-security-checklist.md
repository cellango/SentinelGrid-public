# Production Security Checklist

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**CRITICAL:** Do not deploy to production without completing this checklist!

## Phase 0 Alignment Note

This is an operational hardening checklist, not the scope-setting source of truth.

Use it together with:

- `docs/archive/reference/platform/production-launch-scope-decision-2026-04-15.md`
- `docs/archive/reference/platform/production-risk-register-2026-04-15.md`
- `docs/PRODUCTION_REMEDIATION_IMPLEMENTATION_PLAN.md`
- `docs/archive/reference/platform/production-truth-baseline-2026-04-15.md`

If this checklist conflicts with the current launch boundary or P0 security priorities, the Phase 0 baseline documents win.

---

## 🔐 Keycloak Security

### 1. Change Master Admin Password

**DO NOT use default admin/admin in production!**

```bash
# Option 1: Change via environment variable before first start
export KEYCLOAK_ADMIN_PASSWORD="$(openssl rand -base64 32)"

# Option 2: Change after deployment using seed script
python3 backend/scripts/seed_realms.py \
  --admin-user admin \
  --admin-password admin \
  --new-admin-password "YOUR_SECURE_PASSWORD"

# Option 3: Change via Keycloak Admin Console
# 1. Login to http://your-keycloak/admin
# 2. Master realm → Users → admin
# 3. Credentials tab → Reset Password
```

**Store the new password securely:**
- Use a password manager
- Store in secrets management system (AWS Secrets Manager, Azure Key Vault, etc.)
- Never commit to git

### 2. Update Platform Admin Password

**DO NOT use admin123 in production!**

```bash
# Generate secure password
PLATFORM_ADMIN_PASSWORD="$(openssl rand -base64 24)"

# Update in seed script or Keycloak Admin Console
# After seeding, change password:
# 1. Login to Keycloak Admin
# 2. Select sg-admin realm
# 3. Users → admin@sentinelgrid.ai
# 4. Credentials → Reset Password
```

### 3. Rotate Service Account Secrets

**Retrieve and secure service account client secrets:**

```bash
# Get service account secrets from Keycloak
# 1. Keycloak Admin → sg-admin realm → Clients
# 2. Select: sentinelgrid-platform-api
# 3. Credentials tab → Copy Client Secret
# 4. Store in environment variable or secrets manager

# Same for sentinelgrid-iam-agent client in each realm
```

**Store secrets:**
```bash
# In production, use secrets management
export PLATFORM_API_CLIENT_SECRET="retrieved-from-keycloak"
export IAM_AGENT_CLIENT_SECRET="retrieved-from-keycloak"
```

### 4. Enable HTTPS Only

```yaml
# docker-compose.prod.yml
keycloak:
  command:
    - start
    - --https-port=8443
    - --https-certificate-file=/opt/keycloak/certs/keycloak.crt
    - --https-certificate-key-file=/opt/keycloak/certs/keycloak.key
    - --http-enabled=false  # DISABLE HTTP in production!
```

### 5. Restrict CORS Origins

```python
# backend/services/*/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.sentinelgrid.com",
        "https://admin.sentinelgrid.com"
    ],  # DO NOT use ["*"] in production!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

## 🗄️ Database Security

### 1. Change Database Passwords

```bash
# PostgreSQL application database
export DB_PASSWORD="$(openssl rand -base64 32)"

# Keycloak database
export KEYCLOAK_DB_PASSWORD="$(openssl rand -base64 32)"

# Update docker-compose.prod.yml with new passwords
```

### 2. Enable SSL for Database Connections

```python
# backend/libs/sg_core/db.py
engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"}  # Require SSL in production
)
```

### 3. Restrict Database Access

```bash
# Allow only from application containers
# Configure PostgreSQL pg_hba.conf
host    all    all    172.0.0.0/8    scram-sha-256
hostssl all    all    0.0.0.0/0      scram-sha-256
```

---

## 🔑 API Security

### 1. Generate Strong Internal Service Token

```bash
# DO NOT use the default token in production!
export INTERNAL_SERVICE_TOKEN="$(openssl rand -hex 64)"

# Update in all services via docker-compose.prod.yml or Kubernetes secrets
```

### 2. Enable Rate Limiting

```python
# backend/agents/iam_agent/app/main.py
app.add_middleware(
    RateLimitMiddleware,
    enabled=True,  # Enable in production
    rate="100/minute"
)
```

### 3. Configure JWT Token Lifetimes

```bash
# In Keycloak realm settings (per realm):
Access Token Lifespan: 15 minutes (production)
SSO Session Idle: 30 minutes
SSO Session Max: 10 hours
```

---

## 🌐 Network Security

### 1. Use Real SSL/TLS Certificates

```bash
# Get certificates from Let's Encrypt or your CA
certbot certonly --standalone -d keycloak.sentinelgrid.com
certbot certonly --standalone -d app.sentinelgrid.com

# Mount in docker-compose
volumes:
  - /etc/letsencrypt/live/keycloak.sentinelgrid.com:/opt/keycloak/certs:ro
```

### 2. Configure Firewall Rules

```bash
# Only expose necessary ports:
# - 443 (HTTPS - frontend/keycloak)
# - No direct PostgreSQL access from internet
# - No direct Redis access from internet
# - Internal services communicate via private network
```

### 3. Enable Security Headers

```nginx
# nginx.conf
add_header X-Frame-Options "DENY";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'";
```

---

## 📝 Secrets Management

### Recommended Approach

**Development:**
- Use `.env` file (gitignored)
- Store in `backend/scripts/SEEDED_CREDENTIALS.txt` (gitignored)

**Production:**
- Use secrets management system:
  - AWS Secrets Manager
  - Azure Key Vault
  - Google Secret Manager
  - HashiCorp Vault
  - Kubernetes Secrets

### Environment Variables for Production

```bash
# Critical secrets to set:
KEYCLOAK_ADMIN_PASSWORD="secure-generated-password"
DB_PASSWORD="secure-generated-password"
KEYCLOAK_DB_PASSWORD="secure-generated-password"
INTERNAL_SERVICE_TOKEN="secure-generated-token"
IAM_AGENT_CLIENT_SECRET="from-keycloak-console"
PLATFORM_API_CLIENT_SECRET="from-keycloak-console"

# Service account passwords
PLATFORM_ADMIN_PASSWORD="secure-generated-password"

# External service credentials
SMTP_PASSWORD="your-smtp-password"
NVD_API_KEY="your-nvd-api-key"
```

---

## 🔒 Realm-Specific Security

### Platform Admin Realm (`sg-admin`)

- ✅ Only SentinelGrid staff should have access
- ✅ Enable MFA for all platform admins
- ✅ Strong password policy (12+ chars, special characters)
- ✅ Short token lifetime (15 minutes)
- ✅ Audit all admin actions

### Multi-Tenant Realms (`sg-mt-*`)

- ✅ Enforce tenant isolation via `tenant_id`
- ✅ Disable duplicate emails
- ✅ Enable email verification
- ✅ Standard password policy (8+ chars)
- ✅ Session timeout: 30 minutes idle

### Enterprise Realms (`sg-ent-*`)

- ✅ Custom password policies per customer
- ✅ Support customer SSO (SAML/OIDC)
- ✅ Customer-specific MFA requirements
- ✅ Custom token lifetimes
- ✅ Customer branding

---

## 🎯 Pre-Production Checklist

Before deploying to production:

### Keycloak
- [ ] Master admin password changed
- [ ] Platform admin password changed
- [ ] Service account secrets rotated
- [ ] HTTP disabled (HTTPS only)
- [ ] Real SSL/TLS certificates installed
- [ ] Realm password policies configured
- [ ] Token lifetimes configured
- [ ] Email server configured
- [ ] Backup procedures tested

### Database
- [ ] Database passwords changed
- [ ] SSL/TLS enabled for connections
- [ ] Firewall rules configured
- [ ] Backup procedures in place
- [ ] Monitoring enabled

### Application
- [ ] Internal service token changed
- [ ] CORS origins restricted
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Error messages sanitized (no stack traces to users)
- [ ] Security headers configured

### Infrastructure
- [ ] Firewall configured
- [ ] VPC/Network isolation
- [ ] Load balancer configured
- [ ] DDoS protection enabled
- [ ] Intrusion detection enabled

### Monitoring
- [ ] Realm capacity alerts
- [ ] Failed login monitoring
- [ ] API rate limit monitoring
- [ ] Database connection monitoring
- [ ] Service health checks

### Documentation
- [ ] Runbooks created
- [ ] Incident response plan
- [ ] Disaster recovery plan
- [ ] Secrets rotation procedures

---

## 🔄 Password Rotation Schedule

Implement regular password rotation:

| Credential | Rotation Frequency | Responsibility |
|------------|-------------------|----------------|
| Keycloak master admin | 90 days | Platform team |
| Platform admin users | 90 days | Individual users |
| Service account secrets | 180 days | Platform team |
| Database passwords | 180 days | Platform team |
| Internal service token | 90 days | Platform team |
| SSL/TLS certificates | Before expiry | Platform team |

---

## 🚨 Security Incident Response

If credentials are compromised:

### 1. Immediate Actions
```bash
# Revoke all tokens
# Change affected passwords
# Rotate service account secrets
# Review audit logs for unauthorized access
```

### 2. Investigation
```sql
-- Check audit logs
SELECT * FROM tenant_provisioning_log 
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- Check failed login attempts
-- (Would need to query Keycloak events or implement logging)
```

### 3. Remediation
- Reset affected credentials
- Notify affected customers
- Review security policies
- Implement additional controls

---

## 📖 Additional Resources

- [Keycloak Security Hardening](https://www.keycloak.org/docs/latest/server_admin/#_hardening)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)

---

**Security is not a one-time task - it's an ongoing process!**

Review and update security measures regularly.

---

**Last Updated:** April 15, 2026  
**Review Frequency:** Quarterly  
**Next Review:** July 15, 2026
