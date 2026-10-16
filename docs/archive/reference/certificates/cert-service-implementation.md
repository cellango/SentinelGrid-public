# Certificate Service Implementation

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

The Certificate Service is a microservice that issues, renews, and revokes X.509 certificates for SentinelGrid services and agents. It provides mTLS (mutual TLS) capabilities for internal service-to-service communication and agent-to-backend communication.

## Architecture

### Components

1. **Cert Service** - FastAPI microservice that manages certificate lifecycle
2. **CA Backend** - Step-CA (Smallstep Certificates) for certificate issuance
3. **Database** - PostgreSQL for certificate metadata and audit trails

### Design Principles

- **Pluggable CA Providers** - Support for Step-CA (default) and AWS ACM Private CA (future)
- **Internal API Only** - All endpoints are internal, protected by service tokens
- **Short-Lived Certificates** - Default 30 days for agents, 90 days for services
- **Automatic Renewal** - Services/agents can renew certificates before expiry

## Database Schema

### Tables

- **ca_authorities** - CA backend configurations (Step-CA, AWS ACM PCA, etc.)
- **certificates** - Issued certificates with metadata
- **certificate_requests** - Enrollment requests for audit
- **agent_bootstrap_tokens** - One-time tokens for agent enrollment

## API Endpoints

### Service Enrollment

```http
POST /api/v1/certificates/enroll-service
Authorization: Bearer <service-token>
Content-Type: application/json

{
  "service_id": "siem-agent-1",
  "service_type": "siem-agent",
  "subject_cn": "siem-agent.sentinelgrid.internal",
  "dns_names": ["siem-agent", "siem-agent.sentinelgrid.internal"],
  "ip_addresses": ["10.0.1.10"],
  "ttl_hours": 2160,
  "csr_pem": "-----BEGIN CERTIFICATE REQUEST-----..."  # Optional
}
```

Response:
```json
{
  "certificate_id": "uuid",
  "certificate_pem": "-----BEGIN CERTIFICATE-----...",
  "private_key_pem": null,  // Only if Cert Service generated keypair
  "ca_chain_pem": "-----BEGIN CERTIFICATE-----...",
  "serial_number": "1234567890",
  "expires_at": "2024-02-01T00:00:00Z",
  "spki_fingerprint": "sha256:..."
}
```

### Agent Enrollment

```http
POST /api/v1/certificates/enroll-agent
Content-Type: application/json

{
  "bootstrap_token": "one-time-token-from-ui",
  "agent_id": "agent-123",
  "hostname": "customer-host-1",
  "ip": "192.168.1.100",
  "dns_names": ["customer-host-1.example.com"]
}
```

Response includes `private_key_pem` (agent certs always include private key).

### Certificate Renewal

```http
POST /api/v1/certificates/renew
Authorization: Bearer <service-token>
Content-Type: application/json

{
  "certificate_id": "uuid"
}
```

### Certificate Revocation

```http
POST /api/v1/certificates/{certificate_id}/revoke
Authorization: Bearer <service-token>
Content-Type: application/json

{
  "reason": "key_compromise"  // or "unspecified", "superseded", etc.
}
```

### Get Certificate

```http
GET /api/v1/certificates/{certificate_id}
Authorization: Bearer <service-token>
```

### Create Bootstrap Token

```http
POST /api/v1/bootstrap-tokens
Authorization: Bearer <service-token>
Content-Type: application/json

{
  "tenant_id": "uuid",
  "agent_id": "agent-123",  // Optional
  "ttl_hours": 24
}
```

## Step-CA Setup

### Initial Configuration

1. **Generate Root CA** (one-time, offline):
   ```bash
   docker run -it --rm -v step_ca_data:/home/step smallstep/step-ca step ca init
   ```

2. **Start Step-CA**:
   ```bash
   docker-compose up step-ca
   ```

3. **Configure Provisioner**:
   - Create provisioner in Step-CA config
   - Set provisioner password in environment variables

### Configuration Files

Step-CA configuration is stored in `step_ca_data` volume:
- `config/ca.json` - CA configuration
- `secrets/` - Private keys (root CA, intermediate CA)

## Usage Examples

### Service Enrollment (Python)

```python
import httpx
import os

# Get service token from environment
service_token = os.getenv("INTERNAL_SERVICE_TOKEN")

# Enroll service
response = httpx.post(
    "http://cert-service:8000/api/v1/certificates/enroll-service",
    headers={"Authorization": f"Bearer {service_token}"},
    json={
        "service_id": "siem-agent-1",
        "service_type": "siem-agent",
        "subject_cn": "siem-agent.sentinelgrid.internal",
        "dns_names": ["siem-agent", "siem-agent.sentinelgrid.internal"],
        "ttl_hours": 2160
    }
)

result = response.json()
cert_pem = result["certificate_pem"]
ca_chain_pem = result["ca_chain_pem"]

# Save certificate and configure HTTP client
with open("/etc/certs/service.crt", "w") as f:
    f.write(cert_pem)
with open("/etc/certs/ca.crt", "w") as f:
    f.write(ca_chain_pem)

# Configure httpx client with mTLS
client = httpx.Client(
    cert=("/etc/certs/service.crt", "/etc/certs/service.key"),
    verify="/etc/certs/ca.crt"
)
```

### Agent Enrollment

1. **Create Bootstrap Token** (in UI or via API):
   ```bash
   curl -X POST http://cert-service:8000/api/v1/bootstrap-tokens \
     -H "Authorization: Bearer <service-token>" \
     -H "Content-Type: application/json" \
     -d '{
       "tenant_id": "tenant-uuid",
       "ttl_hours": 24
     }'
   ```

2. **Agent Enrolls**:
   ```bash
   curl -X POST http://cert-service:8000/api/v1/certificates/enroll-agent \
     -H "Content-Type: application/json" \
     -d '{
       "bootstrap_token": "token-from-step-1",
       "agent_id": "agent-123",
       "hostname": "customer-host-1",
       "ip": "192.168.1.100"
     }'
   ```

3. **Agent Saves Certificate**:
   - Save `certificate_pem` to `/etc/sentinelgrid/agent.crt`
   - Save `private_key_pem` to `/etc/sentinelgrid/agent.key` (secure permissions)
   - Save `ca_chain_pem` to `/etc/sentinelgrid/ca.crt`

## Certificate Lifecycle

### Service Certificates

1. **Enrollment** - Service calls `/enroll-service` on startup
2. **Usage** - Service uses cert for mTLS with other services
3. **Renewal** - Service calls `/renew` when cert < 7 days to expiry
4. **Revocation** - Admin revokes via API if compromised

### Agent Certificates

1. **Bootstrap** - Admin creates bootstrap token in UI
2. **Enrollment** - Agent uses token to enroll and get certificate
3. **Usage** - Agent uses cert for mTLS with backend
4. **Renewal** - Agent calls `/renew` when cert < 7 days to expiry
5. **Revocation** - Admin revokes via API if agent compromised

## Security Considerations

### Private Key Handling

- **Service Certificates**: Private keys generated client-side (via CSR) or server-side (V1 simplification)
- **Agent Certificates**: Private keys generated server-side and sent to agent (V1 simplification)
- **Storage**: Private keys stored securely on service/agent, never in Cert Service database

### Token Security

- Bootstrap tokens are hashed (SHA-256) before storage
- Tokens are single-use (marked as used after enrollment)
- Tokens expire after configured TTL (default 24 hours)

### mTLS Enforcement

- Internal load balancer/gateway requires client certificates
- Certificate validation includes:
  - Valid signature from CA
  - Not expired
  - Not revoked
  - Subject/SAN matches expected values

## Future Enhancements

### Phase 2: AWS ACM Private CA Provider

- Implement `AwsPcaProvider` class
- Support for AWS-managed PKI
- Integration with AWS IAM for access control

### Phase 3: Keycloak Integration

- Monitor Keycloak token signing key expiry
- Automated rotation reminders
- Store Keycloak key metadata in Cert Service

### Phase 4: Public TLS Management

- Integration with cert-manager
- Let's Encrypt automation
- ACM integration for AWS

### Phase 5: Customer-Facing PKI (Future Product)

- Tenant-scoped CAs
- Customer certificate issuance APIs
- VPN/Wi-Fi certificate support

## Troubleshooting

### Certificate Enrollment Fails

1. Check Step-CA is running:
   ```bash
   docker-compose ps step-ca
   curl http://step-ca:9000/health
   ```

2. Check Cert Service logs:
   ```bash
   docker-compose logs cert_service
   ```

3. Verify CA authority configuration:
   ```sql
   SELECT * FROM ca_authorities WHERE status = 'active';
   ```

### Bootstrap Token Invalid

1. Check token hasn't expired:
   ```sql
   SELECT * FROM agent_bootstrap_tokens 
   WHERE token_hash = '<hash>' 
   AND expires_at > NOW();
   ```

2. Check token hasn't been used:
   ```sql
   SELECT used_at FROM agent_bootstrap_tokens 
   WHERE token_hash = '<hash>';
   ```

### Certificate Renewal Fails

1. Check certificate status:
   ```sql
   SELECT status, expires_at FROM certificates WHERE id = '<cert-id>';
   ```

2. Verify certificate is not revoked:
   ```sql
   SELECT revoked_at FROM certificates WHERE id = '<cert-id>';
   ```

## Related Files

- `backend/migrations/008_cert_service.sql` - Database schema
- `backend/services/cert_service/` - Service implementation
- `docker-compose.dev.yml` - Service and Step-CA configuration
- `docs/archive/reference/certificates/cert-service-quick-start.md` - Quick start guide

