# IAM Deployment Runbook - Production Ready

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Date:** December 3, 2025  
**Status:** Production Ready ✅

---

## Pre-Deployment Checklist

### Code Readiness

- [x] KeycloakAdminClient implemented and tested
- [x] User management APIs complete
- [x] Role management APIs complete
- [x] MFA implementation complete
- [x] Audit log query API complete
- [x] Multi-tenant isolation tests passing (50+)
- [x] E2E tests passing
- [x] All linter errors resolved
- [x] Code review completed
- [x] Security review completed

### Documentation Readiness

- [x] API reference complete
- [x] Multi-tenant security guide
- [x] MFA setup guide
- [x] Deployment runbook (this document)
- [x] Troubleshooting guides

### Infrastructure Readiness

- [ ] Keycloak v26.4.7 deployed
- [ ] PostgreSQL database ready
- [ ] Redis cache ready
- [ ] Load balancer configured
- [ ] SSL certificates installed
- [ ] DNS configured
- [ ] Monitoring setup
- [ ] Alerting configured

---

## Deployment Steps

### Step 1: Deploy Keycloak v26.4.7

```bash
# 1. Start Keycloak with PostgreSQL backend
docker-compose -f docker-compose.prod.yml up -d keycloak keycloak_db

# 2. Wait for Keycloak to start (check health)
curl http://keycloak:8080/health/ready

# 3. Create sentinelgrid realm
docker exec keycloak /opt/keycloak/bin/kcadm.sh \
  config credentials --server http://localhost:8080 --realm master \
  --user admin --password $KEYCLOAK_ADMIN_PASSWORD

docker exec keycloak /opt/keycloak/bin/kcadm.sh \
  create realms -s realm=sentinelgrid -s enabled=true

# 4. CRITICAL: Configure User Profile
bash scripts/configure_user_profile.sh

# 5. Create roles
for role in TENANT_ADMIN SOC_MANAGER SOC_ANALYST VIEW_ONLY; do
  docker exec keycloak /opt/keycloak/bin/kcadm.sh \
    create roles -r sentinelgrid -s name=$role
done

# 6. Create clients (web, api)
# See scripts/setup-keycloak-clients.sh

# 7. Configure protocol mappers
# See scripts/configure-protocol-mappers.sh
```

---

### Step 2: Deploy IAM Agent

```bash
# 1. Build Docker image
cd backend/agents/iam_agent
docker build -t sentinelgrid/iam-agent:latest .

# 2. Set environment variables
export KEYCLOAK_URL=https://auth.sentinelgrid.ai
export KEYCLOAK_REALM=sentinelgrid
export KEYCLOAK_ADMIN_USER=admin
export KEYCLOAK_ADMIN_PASSWORD=<secure-password>
export DB_URL=postgresql://user:pass@db:5432/sentinelgrid
export REDIS_URL=redis://redis:6379

# 3. Start IAM Agent
docker-compose -f docker-compose.prod.yml up -d iam_agent

# 4. Verify health
curl http://iam-agent:8000/internal/iam/auth/health
```

---

### Step 3: Deploy Entitlement Agent

```bash
# 1. Run database migrations
cd backend/services/entitlement_agent
docker-compose run --rm flyway migrate

# 2. Start Entitlement Agent
docker-compose -f docker-compose.prod.yml up -d entitlement_agent

# 3. Verify health
curl http://entitlement-agent:8001/health
```

---

### Step 4: Run Security Tests

**CRITICAL:** Run full security test suite before going live

```bash
cd backend

# 1. Multi-tenant isolation tests (MUST PASS)
pytest tests/test_multi_tenant_isolation.py -v

# Expected: All 50+ tests PASS, 0 failures

# 2. E2E auth tests
pytest tests/test_e2e_auth_complete.py -v

# 3. E2E authorization tests
pytest tests/test_e2e_authorization_complete.py -v

# 4. Verify tenant_id persistence
python3 scripts/test_tenant_id_attribute.py

# Expected: ✅ All tests passed
```

**DO NOT PROCEED if any security test fails!**

---

### Step 5: Create First Production Tenant

```bash
# Use signup API to create first customer
curl -X POST https://api.sentinelgrid.ai/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "First Customer",
    "email": "admin@firstcustomer.com",
    "password": "SecurePassword123!",
    "first_name": "Admin",
    "last_name": "User",
    "employee_count": 100
  }'

# Verify tenant_id in response
# Verify login works
# Verify JWT token contains tenant_id
```

---

### Step 6: Enable Monitoring

```bash
# 1. Start Prometheus/Grafana
docker-compose up -d prometheus grafana

# 2. Configure alerts for:
#    - tenant_isolation_violations (CRITICAL)
#    - 403_responses_spike (HIGH)
#    - invalid_token_rate (MEDIUM)

# 3. Create dashboards:
#    - User signups per day
#    - Active users per tenant
#    - Authorization decision rate
#    - MFA enrollment rate
```

---

## Post-Deployment Verification

### Test Checklist (Production)

```bash
# 1. Signup new user
curl -X POST https://api.sentinelgrid.ai/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Test", "email": "test@example.com", ...}'

# 2. Login
curl -X POST https://api.sentinelgrid.ai/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "..."}'

# 3. Verify tenant_id in token
# Decode JWT at jwt.io - verify tenant_id claim present

# 4. Call protected API
curl -X GET https://api.sentinelgrid.ai/api/v1/users \
  -H "Authorization: Bearer {token}"

# 5. Verify audit logs
curl -X GET https://api.sentinelgrid.ai/api/v1/audit-logs \
  -H "Authorization: Bearer {token}"

# 6. Test MFA enrollment
curl -X POST https://api.sentinelgrid.ai/api/v1/mfa/enroll \
  -H "Authorization: Bearer {token}" \
  -d '{"user_id": "..."}'
```

**Expected Results:**
- ✅ All requests successful
- ✅ tenant_id present in all responses
- ✅ No cross-tenant data visible
- ✅ Audit logs recording events

---

## Rollback Plan

### If Issues Detected

**Immediate Actions:**
1. Stop accepting new signups
2. Investigate issue
3. Notify affected customers (if data exposed)

**Rollback Procedure:**
```bash
# 1. Stop IAM Agent
docker-compose stop iam_agent

# 2. Restore previous version
docker-compose pull iam_agent:previous-version
docker-compose up -d iam_agent

# 3. Verify old version working
curl http://iam-agent:8000/health

# 4. Investigate issue offline
```

---

## Monitoring Dashboard

### Key Metrics

**User Activity:**
- Active users (last 24h)
- Signups per day
- Login success rate
- MFA enrollment rate

**Security:**
- Tenant isolation violations (should be 0)
- Failed auth attempts
- 403 responses per tenant
- Cross-tenant access attempts

**Performance:**
- User creation latency (target: <200ms)
- Token validation latency (target: <50ms)
- Authorization check latency (target: <10ms)
- API response times (p95, p99)

---

## Troubleshooting

### Issue: Users can't login

**Check:**
1. Keycloak is running: `docker ps | grep keycloak`
2. Realm exists: Check Keycloak admin console
3. User exists: Query Keycloak API
4. Password correct: Check audit logs

**Solution:** See `docs/TROUBLESHOOTING_IAM.md`

---

### Issue: tenant_id not in token

**Check:**
1. User Profile configured: `bash scripts/configure_user_profile.sh`
2. User has tenant_id attribute: Check in Keycloak
3. Protocol mapper configured: Check client mappers

**Solution:** Run User Profile configuration script

---

### Issue: MFA not working

**Check:**
1. Keycloak OTP policy configured
2. User has CONFIGURE_TOTP required action
3. MFA credentials exist for user

**Solution:** See `docs/MFA_SETUP_GUIDE.md`

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor security metrics
- Review isolation violation alerts (should be 0)
- Check system health

**Weekly:**
- Review audit logs
- Check for failed auth spikes
- Verify backup integrity

**Monthly:**
- Security review
- Update dependencies
- Review access patterns
- Run security test suite

**Quarterly:**
- Penetration testing
- Security audit
- Compliance review
- Update documentation

---

## Emergency Contacts

**Security Issues:**
- Security team: security@sentinelgrid.ai
- On-call: PagerDuty integration
- Escalation: CTO

**Infrastructure:**
- DevOps team: devops@sentinelgrid.ai
- Database: DBA on-call
- Network: Network team

---

## Success Criteria

### Deployment Successful If:

✅ **Keycloak running** - Health check passing  
✅ **IAM Agent running** - Health check passing  
✅ **Entitlement Agent running** - Health check passing  
✅ **Signup working** - Users can create accounts  
✅ **Login working** - Users can authenticate  
✅ **tenant_id in tokens** - JWT tokens contain tenant_id  
✅ **Multi-tenant isolation** - Security tests passing  
✅ **MFA working** - Enrollment and verification functional  
✅ **Audit logs working** - Events being recorded  
✅ **No errors in logs** - Clean startup  
✅ **Monitoring active** - Metrics being collected  

---

## Conclusion

This runbook provides step-by-step deployment instructions for SentinelGrid's IAM system. Follow all steps carefully, especially security testing.

**DO NOT skip security tests before production deployment.**

**Status:** Ready for Production Deployment ✅  
**Last Updated:** December 3, 2025  
**Next Review:** After first production deployment

