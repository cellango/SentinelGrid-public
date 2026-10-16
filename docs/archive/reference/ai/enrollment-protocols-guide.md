# Enrollment Protocols Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Purpose:** Guide for using ACME, SCEP, and EST enrollment protocols

---

## Overview

SentinelGrid supports three enrollment protocols for automated certificate management:

1. **ACME** - For web servers, Kubernetes, automated renewal
2. **SCEP** - For network devices, routers, firewalls
3. **EST** - For modern devices, IoT, mobile management

All protocols are tenant-scoped and provide secure certificate enrollment.

---

## ACME (Automatic Certificate Management Environment)

### Use Cases
- Web servers (Apache, Nginx)
- Kubernetes clusters (cert-manager)
- Automated certificate renewal
- Let's Encrypt-compatible clients

### Getting ACME Directory URL

**API Endpoint:**
```bash
GET /api/v1/enrollment/acme/directory
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "directory_url": "https://ejbca:8443/ejbca/acme/directory",
  "new_account_url": "https://ejbca:8443/ejbca/acme/newAccount",
  "new_order_url": "https://ejbca:8443/ejbca/acme/newOrder",
  "new_nonce_url": "https://ejbca:8443/ejbca/acme/newNonce",
  "key_change_url": "https://ejbca:8443/ejbca/acme/keyChange",
  "revoke_cert_url": "https://ejbca:8443/ejbca/acme/revokeCert"
}
```

### Using with certbot

```bash
# Get ACME directory URL from API
ACME_DIR=$(curl -H "Authorization: Bearer $TOKEN" \
  https://api.sentinelgrid.com/api/v1/enrollment/acme/directory | jq -r .directory_url)

# Issue certificate via certbot
certbot certonly \
  --server $ACME_DIR \
  --manual \
  --preferred-challenges http \
  -d example.com
```

### Using with cert-manager (Kubernetes)

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: sentinelgrid-ejbca
spec:
  acme:
    server: https://ejbca:8443/ejbca/acme/directory
    email: admin@example.com
    privateKeySecretRef:
      name: sentinelgrid-acme-key
    solvers:
    - http01:
        ingress:
          class: nginx
```

### Using with acme.sh

```bash
# Set ACME directory
export ACME_DIRECTORY="https://ejbca:8443/ejbca/acme/directory"

# Issue certificate
acme.sh --issue -d example.com --server $ACME_DIRECTORY
```

---

## SCEP (Simple Certificate Enrollment Protocol)

### Use Cases
- Network devices (routers, firewalls, switches)
- Legacy devices
- Windows devices
- Cisco, Juniper, Palo Alto devices

### Getting SCEP Endpoint

**API Endpoint:**
```bash
GET /api/v1/enrollment/scep/endpoint
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "scep_endpoint_url": "https://ejbca:8443/ejbca/publicweb/apply/scep/pkiclient.exe",
  "ca_certificate_url": "https://ejbca:8443/ejbca/publicweb/apply/scep/pkiclient.exe?operation=GetCACert",
  "instructions": {
    "description": "SCEP enrollment for network devices",
    "usage": "Use SCEP client to connect to endpoint URL",
    "password": "SCEP password required (configured in EJBCA)"
  }
}
```

### Using with Network Devices

**Cisco Router:**
```cisco
crypto pki trustpoint SentinelGrid
 enrollment url https://ejbca:8443/ejbca/publicweb/apply/scep/pkiclient.exe
 enrollment mode ra
 password <SCEP_PASSWORD>
 revocation-check crl
```

**Juniper:**
```junos
set security pki ca-profile SentinelGrid ca-identity <CA_ID>
set security pki ca-profile SentinelGrid enrollment url https://ejbca:8443/ejbca/publicweb/apply/scep/pkiclient.exe
set security pki ca-profile SentinelGrid enrollment retry 3
```

**Palo Alto:**
```
Device > Certificate Management > Certificates > Device Certificates
- Click "Generate"
- Select "SCEP"
- SCEP URL: https://ejbca:8443/ejbca/publicweb/apply/scep/pkiclient.exe
- SCEP Password: <SCEP_PASSWORD>
```

### Using with Windows

**Via PowerShell:**
```powershell
# Configure SCEP enrollment
$scepUrl = "https://ejbca:8443/ejbca/publicweb/apply/scep/pkiclient.exe"
certutil -config $scepUrl -ping
```

**Via Group Policy:**
1. Computer Configuration > Policies > Windows Settings > Security Settings > Public Key Policies
2. Certificate Services Client - Certificate Enrollment Policy
3. Add SCEP enrollment policy with URL

---

## EST (Enrollment over Secure Transport)

### Use Cases
- Modern network devices
- IoT devices
- Mobile device management (MDM)
- Devices supporting EST protocol

### Getting EST Endpoints

**API Endpoint:**
```bash
GET /api/v1/enrollment/est/cacerts
Authorization: Bearer <JWT_TOKEN>
```

**Response:**
```json
{
  "cacerts_url": "https://ejbca:8443/.well-known/est/cacerts",
  "simpleenroll_url": "https://ejbca:8443/.well-known/est/simpleenroll",
  "simplereenroll_url": "https://ejbca:8443/.well-known/est/simplereenroll",
  "instructions": {
    "description": "EST enrollment for modern devices",
    "usage": "Use EST client to connect to endpoints",
    "authentication": "Client certificate or username/password"
  }
}
```

### Using with EST Client

**Python Example:**
```python
import requests
from cryptography import x509
from cryptography.hazmat.primitives import serialization

# Get CA certificates
response = requests.get("https://ejbca:8443/.well-known/est/cacerts", verify=False)
ca_certs = response.content

# Enroll certificate
csr = generate_csr()  # Your CSR generation code
response = requests.post(
    "https://ejbca:8443/.well-known/est/simpleenroll",
    data=csr,
    headers={"Content-Type": "application/pkcs10"},
    auth=("username", "password"),
    verify=False
)
certificate = response.content
```

### Using with Network Devices

**Modern Cisco Devices:**
```cisco
crypto pki trustpoint SentinelGrid-EST
 enrollment url https://ejbca:8443/.well-known/est/simpleenroll
 enrollment mode est
```

---

## Protocol Comparison

| Feature | ACME | SCEP | EST |
|---------|------|------|-----|
| **Use Case** | Web servers, K8s | Network devices | Modern devices |
| **Protocol** | HTTP/HTTPS | HTTP/HTTPS | HTTPS only |
| **Authentication** | Account key | Password | Certificate/Password |
| **Challenge Types** | HTTP-01, DNS-01 | Password | Certificate |
| **Renewal** | Automatic | Manual/RA | Automatic |
| **Standards** | RFC 8555 | RFC 8894 | RFC 7030 |
| **Client Support** | certbot, cert-manager | Network devices | EST clients |

---

## Tenant Isolation

All enrollment protocols are tenant-scoped:

- **ACME:** Each tenant can have their own ACME alias (optional)
- **SCEP:** Each tenant can have their own SCEP RA (optional)
- **EST:** Each tenant can have their own EST alias (optional)

If per-tenant aliases are not configured, tenants share the default endpoints but certificates are still tenant-isolated via database filtering.

---

## Configuration

### EJBCA Configuration

**ACME Setup:**
1. Navigate to: **System Configuration → External RA → ACME**
2. Enable ACME
3. Create ACME alias (optional per tenant)
4. Configure certificate profile
5. Save

**SCEP Setup:**
1. Navigate to: **System Configuration → External RA → SCEP**
2. Enable SCEP
3. Create SCEP RA (optional per tenant)
4. Configure SCEP password
5. Save

**EST Setup:**
1. Navigate to: **System Configuration → External RA → EST**
2. Enable EST
3. Create EST alias (optional per tenant)
4. Configure authentication
5. Save

### Environment Variables

```bash
# ACME Configuration
EJBCA_ACME_ALIAS=sentinelgrid-acme  # Optional per-tenant alias

# SCEP Configuration
EJBCA_SCEP_RA_NAME=SentinelGrid-SCEP-RA  # Optional SCEP RA name

# EST Configuration
EJBCA_EST_ALIAS=sentinelgrid-est  # Optional EST alias
```

---

## Testing

### Test ACME

```bash
# Get ACME directory
curl -H "Authorization: Bearer $TOKEN" \
  https://api.sentinelgrid.com/api/v1/enrollment/acme/directory

# Test with certbot (staging)
certbot certonly --server https://ejbca:8443/ejbca/acme/directory \
  --manual --preferred-challenges http -d test.example.com
```

### Test SCEP

```bash
# Get SCEP endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://api.sentinelgrid.com/api/v1/enrollment/scep/endpoint

# Test CA certificate retrieval
curl -k https://ejbca:8443/ejbca/publicweb/apply/scep/pkiclient.exe?operation=GetCACert
```

### Test EST

```bash
# Get EST endpoints
curl -H "Authorization: Bearer $TOKEN" \
  https://api.sentinelgrid.com/api/v1/enrollment/est/cacerts

# Test CA certificates
curl -k https://ejbca:8443/.well-known/est/cacerts
```

---

## Security Considerations

### Authentication
- **ACME:** Uses account key pairs (asymmetric crypto)
- **SCEP:** Uses password (configured in EJBCA)
- **EST:** Uses client certificate or username/password

### Transport Security
- All protocols use HTTPS
- Self-signed certificates in development (accept warnings)
- Valid certificates required in production

### Tenant Isolation
- Certificates are tenant-scoped in database
- Per-tenant protocol aliases provide additional isolation
- Shared endpoints still enforce tenant isolation via database

---

## Troubleshooting

### ACME Issues

**"ACME directory not found":**
- Verify ACME is enabled in EJBCA
- Check ACME alias configuration
- Verify URL is correct

**"Challenge failed":**
- Check HTTP-01 challenge accessibility
- Verify DNS-01 challenge permissions
- Check certificate profile configuration

### SCEP Issues

**"SCEP password incorrect":**
- Verify SCEP password in EJBCA
- Check SCEP RA configuration
- Verify device SCEP password matches

**"CA certificate not found":**
- Verify CA is active in EJBCA
- Check SCEP RA CA assignment
- Verify endpoint URL

### EST Issues

**"EST endpoint not found":**
- Verify EST is enabled in EJBCA
- Check EST alias configuration
- Verify URL path (.well-known/est)

**"Authentication failed":**
- Verify client certificate or credentials
- Check EST authentication configuration
- Verify username/password

---

## Next Steps

1. Configure ACME/SCEP/EST in EJBCA Admin UI
2. Test enrollment with each protocol
3. Document tenant-specific configurations
4. Create enrollment wizards in UI (Phase 4)

---

**Last Updated:** 2025-01-28

