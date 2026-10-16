# Certificate Service Quick Start

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

This guide helps you get the Certificate Service up and running quickly for development and testing.

## Prerequisites

- Docker and Docker Compose
- PostgreSQL running (via docker-compose)
- Step-CA container (included in docker-compose)

## Quick Setup

### 1. Run Database Migration

```bash
psql -U sg -d sg -f backend/migrations/008_cert_service.sql
```

### 2. Start Services

```bash
docker-compose up -d step-ca cert_service
```

### 3. Initialize Step-CA (First Time Only)

```bash
# Generate root CA and intermediate CA
docker exec -it sentinelgrid-step-ca-1 step ca init \
  --name "SentinelGrid Internal CA" \
  --dns "step-ca" \
  --address ":9000" \
  --provisioner "sentinelgrid" \
  --password-file /dev/stdin <<< "change-me-in-production"
```

### 4. Verify Services

```bash
# Check Step-CA health
curl http://localhost:9000/health

# Check Cert Service health
curl http://localhost:8015/health
```

## Testing Certificate Enrollment

### Test Service Enrollment

```bash
curl -X POST http://localhost:8015/api/v1/certificates/enroll-service \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "test-service-1",
    "service_type": "test-service",
    "subject_cn": "test-service.sentinelgrid.internal",
    "dns_names": ["test-service", "test-service.sentinelgrid.internal"],
    "ttl_hours": 720
  }'
```

### Test Agent Enrollment

1. **Create Bootstrap Token**:
   ```bash
   curl -X POST http://localhost:8015/api/v1/bootstrap-tokens \
     -H "Authorization: Bearer ${ACCESS_TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{
       "tenant_id": "00000000-0000-0000-0000-000000000000",
       "ttl_hours": 24
     }'
   ```
   
   Save the `token` from the response.

2. **Enroll Agent**:
   ```bash
   curl -X POST http://localhost:8015/api/v1/certificates/enroll-agent \
     -H "Content-Type: application/json" \
     -d '{
       "bootstrap_token": "<token-from-step-1>",
       "agent_id": "test-agent-1",
       "hostname": "test-host",
       "ip": "192.168.1.100"
     }'
   ```

## Configuration

### Environment Variables

**Cert Service**:
- `CA_BACKEND_TYPE` - CA backend type (default: `step-ca`)
- `STEP_CA_URL` - Step-CA API URL (default: `http://step-ca:9000`)
- `STEP_CA_PROVISIONER_NAME` - Provisioner name (default: `sentinelgrid`)
- `STEP_CA_PROVISIONER_PASSWORD` - Provisioner password
- `INTERNAL_SERVICE_TOKEN` - Service authentication token
- `SERVICE_CERT_TTL_HOURS` - Service cert TTL (default: 2160 = 90 days)
- `AGENT_CERT_TTL_HOURS` - Agent cert TTL (default: 720 = 30 days)

**Step-CA**:
- `STEP_CA_PROVISIONER_PASSWORD` - Provisioner password
- Volume: `step_ca_data` - Contains CA configuration and keys

## Next Steps

1. **Integrate with Services**: Update services to enroll on startup
2. **Configure mTLS**: Update load balancer/gateway to require client certs
3. **Set Up Auto-Renewal**: Implement renewal logic in services/agents
4. **Monitor Expiry**: Set up alerts for certificates expiring soon

## Common Issues

### Step-CA Not Starting

- Check logs: `docker-compose logs step-ca`
- Verify volume exists: `docker volume ls | grep step_ca`
- Re-initialize if needed (see step 3 above)

### Certificate Enrollment Fails

- Verify Step-CA is healthy: `curl http://localhost:9000/health`
- Check Cert Service logs: `docker-compose logs cert_service`
- Verify database connection and tables exist

### Bootstrap Token Invalid

- Check token hasn't expired (default 24 hours)
- Verify token hasn't been used already
- Check tenant_id matches

## Production Considerations

⚠️ **Important for Production**:

1. **Change Default Passwords**:
   - Set `STEP_CA_PROVISIONER_PASSWORD` to a strong password
   - Set `INTERNAL_SERVICE_TOKEN` to a secure token

2. **Secure CA Keys**:
   - Root CA key should be stored offline/HSM
   - Intermediate CA key should be in secure storage (KMS/HSM)

3. **Network Security**:
   - Cert Service should only be accessible internally
   - Use mTLS for Cert Service API (bootstrap with initial cert)

4. **Monitoring**:
   - Monitor certificate expiry
   - Alert on failed enrollments
   - Track certificate usage

5. **Backup**:
   - Backup CA keys securely
   - Backup certificate database regularly

