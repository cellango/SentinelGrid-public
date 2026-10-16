# Public Certificate Support - Implementation Plan

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Status:** 📋 Planning Phase  
**Goal:** Support both private (EJBCA) and public (paid) certificate issuance

---

## Overview

SentinelGrid will support two types of certificate issuance:

1. **Private Certificates (EJBCA)** - For internal services, mTLS, devices
   - Issued by our private CA (EJBCA)
   - Free for customers
   - Not trusted by browsers/OS by default
   - Stored in database

2. **Public Certificates (Paid Services)** - For public-facing websites
   - Issued by public CAs (DigiCert, Sectigo, Let's Encrypt, etc.)
   - Paid service (customer pays)
   - Trusted by browsers/OS
   - Stored in Vault (sensitive)

---

## Public Certificate Provider Options

### Option 1: Let's Encrypt (Free, Automated)
- **Cost:** Free
- **API:** ACME protocol
- **Use Case:** Public websites, automated renewal
- **Limitations:** Rate limits, 90-day validity
- **Integration:** ACME client (certbot, acme.sh)

### Option 2: DigiCert (Paid, Enterprise)
- **Cost:** ~$200-500/year per certificate
- **API:** REST API
- **Use Case:** Enterprise customers, EV certificates
- **Features:** Wildcard, EV, OV certificates
- **Integration:** DigiCert API

### Option 3: Sectigo (Paid, Mid-Market)
- **Cost:** ~$50-200/year per certificate
- **API:** REST API
- **Use Case:** SMB customers, standard certificates
- **Features:** Wildcard, multi-domain
- **Integration:** Sectigo API

### Option 4: AWS Certificate Manager (PaID, Cloud)
- **Cost:** Free for AWS services, $400/year for public certs
- **API:** AWS SDK
- **Use Case:** AWS-hosted services
- **Features:** Automatic renewal, AWS integration
- **Integration:** boto3

**Recommendation:** Start with Let's Encrypt (free) + DigiCert (paid option), add more providers as needed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Certificate Request UI                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Certificate Type Selection                          │   │
│  │  ○ Private (EJBCA) - Free                            │   │
│  │  ● Public (Paid) - $X/year                           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Certificate Service                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Provider Selection                                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │   │
│  │  │  EJBCA   │  │ Let's     │  │ DigiCert │         │   │
│  │  │ Provider │  │ Encrypt   │  │ Provider │         │   │
│  │  │          │  │ Provider  │  │          │         │   │
│  │  └──────────┘  └──────────┘  └──────────┘         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────────┐          ┌──────────────────────┐
│   EJBCA Platform      │          │  Public CA API        │
│   (Private CA)        │          │  (DigiCert, etc.)     │
└──────────────────────┘          └──────────────────────┘
        │                                       │
        │                                       │
        ▼                                       ▼
┌──────────────────────┐          ┌──────────────────────┐
│   Database Storage    │          │   Vault Storage      │
│   (Certificate Meta)  │          │   (Cert + Private    │
│                       │          │    Key)              │
└──────────────────────┘          └──────────────────────┘
```

---

## Database Schema Updates

### Certificate Model Enhancement

```sql
-- Add certificate_type to certificates table
ALTER TABLE certificates 
  ADD COLUMN certificate_type VARCHAR(50) NOT NULL DEFAULT 'private',  -- 'private' or 'public'
  ADD COLUMN public_provider VARCHAR(50),  -- 'letsencrypt', 'digicert', 'sectigo', etc.
  ADD COLUMN public_order_id VARCHAR(255),  -- Order ID from public CA
  ADD COLUMN vault_path VARCHAR(500),  -- Vault path for public certs
  ADD COLUMN cost_cents INTEGER,  -- Cost in cents (for public certs)
  ADD COLUMN billing_status VARCHAR(50);  -- 'pending', 'billed', 'failed'

-- Index for certificate type queries
CREATE INDEX idx_certificates_certificate_type ON certificates(certificate_type);
CREATE INDEX idx_certificates_public_provider ON certificates(public_provider);
```

### Public Certificate Orders Table

```sql
CREATE TABLE public_certificate_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  certificate_id UUID REFERENCES certificates(id) ON DELETE SET NULL,
  provider VARCHAR(50) NOT NULL,  -- 'letsencrypt', 'digicert', etc.
  order_id VARCHAR(255) NOT NULL,  -- Provider order ID
  domain VARCHAR(255) NOT NULL,
  validation_method VARCHAR(50),  -- 'dns', 'http', 'email'
  validation_status VARCHAR(50),  -- 'pending', 'validated', 'failed'
  cost_cents INTEGER,
  status VARCHAR(50) NOT NULL,  -- 'pending', 'issued', 'failed', 'cancelled'
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  issued_at TIMESTAMP WITH TIME ZONE,
  expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_public_cert_orders_tenant_id ON public_certificate_orders(tenant_id);
CREATE INDEX idx_public_cert_orders_order_id ON public_certificate_orders(order_id);
CREATE INDEX idx_public_cert_orders_status ON public_certificate_orders(status);
```

---

## Vault Storage Structure

### Public Certificate Storage

**Path Structure:**
```
tenants/{tenant_id}/certificates/public/{certificate_id}/
  ├── certificate.pem
  ├── private_key.pem
  ├── ca_chain.pem
  └── metadata.json
```

**Metadata JSON:**
```json
{
  "provider": "digicert",
  "order_id": "12345",
  "domain": "example.com",
  "issued_at": "2025-01-28T00:00:00Z",
  "expires_at": "2026-01-28T00:00:00Z",
  "cost_cents": 20000,
  "billing_status": "billed"
}
```

---

## Provider Implementations

### Let's Encrypt Provider

**File:** `backend/services/cert_service/app/providers/letsencrypt.py`

```python
"""Let's Encrypt provider using ACME protocol."""

import acme
import acme.client
from app.providers.base import CAProvider, IssueCertRequest, IssueCertResult

class LetsEncryptProvider(CAProvider):
    """Let's Encrypt provider using ACME v2."""
    
    def __init__(self, staging: bool = False):
        self.staging = staging
        self.acme_directory = (
            "https://acme-staging-v02.api.letsencrypt.org/directory"
            if staging
            else "https://acme-v02.api.letsencrypt.org/directory"
        )
    
    def issue_cert(self, request: IssueCertRequest) -> IssueCertResult:
        """Issue certificate via Let's Encrypt ACME."""
        # ACME challenge (HTTP-01 or DNS-01)
        # Issue certificate
        # Return certificate + chain
        pass
    
    def revoke_cert(self, serial_number: str, reason: str = "unspecified") -> bool:
        """Revoke certificate via ACME."""
        pass
```

### DigiCert Provider

**File:** `backend/services/cert_service/app/providers/digicert.py`

```python
"""DigiCert provider using REST API."""

import httpx
from app.providers.base import CAProvider, IssueCertRequest, IssueCertResult

class DigiCertProvider(CAProvider):
    """DigiCert provider using REST API."""
    
    def __init__(self, api_key: str, api_secret: str, organization_id: int):
        self.api_key = api_key
        self.api_secret = api_secret
        self.organization_id = organization_id
        self.base_url = "https://www.digicert.com/services/v2"
    
    def issue_cert(self, request: IssueCertRequest) -> IssueCertResult:
        """Issue certificate via DigiCert API."""
        # Create order
        # Validate domain
        # Issue certificate
        # Return certificate + chain
        pass
    
    def revoke_cert(self, serial_number: str, reason: str = "unspecified") -> bool:
        """Revoke certificate via DigiCert API."""
        pass
```

---

## API Endpoints

### Request Certificate (Updated)

```python
@router.post("/v1/certificates/request", response_model=IssueCertResponse)
async def request_certificate(
    request: CertificateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Request a certificate (private or public).
    
    Request body:
    {
        "certificate_type": "private" | "public",
        "provider": "ejbca" | "letsencrypt" | "digicert",  # Required if public
        "subject_cn": "example.com",
        "dns_names": ["example.com", "www.example.com"],
        ...
    }
    """
    if request.certificate_type == "private":
        # Use EJBCA provider
        provider = get_ejbca_provider(tenant_id)
    elif request.certificate_type == "public":
        # Use public provider
        provider = get_public_provider(request.provider)
    else:
        raise HTTPException(status_code=400, detail="Invalid certificate_type")
    
    # Issue certificate
    result = provider.issue_cert(...)
    
    # Store in appropriate location
    if request.certificate_type == "public":
        # Store in Vault
        store_in_vault(tenant_id, certificate_id, result)
    else:
        # Store in database (already handled)
        pass
    
    return IssueCertResponse(**result)
```

---

## UI Updates

### Certificate Request Form

**File:** `frontend/src/components/certificates/CertificateRequestForm.tsx`

```typescript
interface CertificateRequestFormProps {
  onSubmit: (request: CertificateRequest) => void;
}

export function CertificateRequestForm({ onSubmit }: CertificateRequestFormProps) {
  const [certificateType, setCertificateType] = useState<'private' | 'public'>('private');
  const [provider, setProvider] = useState<string>('ejbca');
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Certificate Type Selection */}
      <div>
        <label>Certificate Type</label>
        <RadioGroup value={certificateType} onChange={setCertificateType}>
          <Radio value="private">
            Private (EJBCA) - Free
            <span className="text-sm text-gray-500">
              For internal services, mTLS, devices
            </span>
          </Radio>
          <Radio value="public">
            Public (Paid) - $X/year
            <span className="text-sm text-gray-500">
              For public websites, trusted by browsers
            </span>
          </Radio>
        </RadioGroup>
      </div>
      
      {/* Provider Selection (if public) */}
      {certificateType === 'public' && (
        <div>
          <label>Certificate Provider</label>
          <Select value={provider} onChange={setProvider}>
            <option value="letsencrypt">Let's Encrypt - Free</option>
            <option value="digicert">DigiCert - $200/year</option>
            <option value="sectigo">Sectigo - $50/year</option>
          </Select>
        </div>
      )}
      
      {/* Certificate Details */}
      <div>
        <label>Domain Name</label>
        <Input name="subject_cn" required />
      </div>
      
      {/* ... rest of form ... */}
    </form>
  );
}
```

---

## Admin Information Storage

### Platform Admin Document Updates

**Location:** `docs/archive/reference/platform/platform-admin-guide.md`

**Add Section: Certificate Management**

```markdown
## Certificate Management

### Certificate Types

**Private Certificates (EJBCA):**
- Issued by SentinelGrid private CA
- Free for customers
- Stored in database
- Used for: internal services, mTLS, devices

**Public Certificates (Paid):**
- Issued by public CAs (DigiCert, Let's Encrypt, etc.)
- Paid service (customer billed)
- Stored in Vault
- Used for: public websites

### Accessing Certificates

**Private Certificates:**
```bash
# Via API
curl -H "Authorization: Bearer $TOKEN" \
  https://api.sentinelgrid.com/api/v1/certificates

# Via Database
psql -c "SELECT * FROM certificates WHERE tenant_id = '$TENANT_ID'"
```

**Public Certificates:**
```bash
# Via Vault
vault kv get tenants/{tenant_id}/certificates/public/{certificate_id}/certificate.pem
```

### Certificate Provider Configuration

**EJBCA:**
- URL: `https://ejbca:8443`
- Admin: Stored in Vault (`sentinelgrid/ejbca/admin-credentials`)

**DigiCert:**
- API Key: Stored in Vault (`sentinelgrid/certificates/digicert/api-key`)
- API Secret: Stored in Vault (`sentinelgrid/certificates/digicert/api-secret`)
- Organization ID: Stored in Vault (`sentinelgrid/certificates/digicert/org-id`)

**Let's Encrypt:**
- No credentials needed (ACME protocol)
- Rate limits: 50 certs/week per domain
```

---

## Testing Strategy

### Test Structure

**File:** `backend/tests/cert_service/`

```
cert_service/
├── __init__.py
├── conftest.py
├── test_certificate_service.py
├── test_ejbca_provider.py
├── test_letsencrypt_provider.py
├── test_digicert_provider.py
├── test_tenant_isolation.py
├── test_vault_storage.py
└── test_public_certificate_flow.py
```

### Test Cases

**1. Private Certificate Tests**
```python
def test_issue_private_certificate():
    """Test issuing private certificate via EJBCA."""
    pass

def test_revoke_private_certificate():
    """Test revoking private certificate."""
    pass

def test_tenant_isolation_private():
    """Test tenant isolation for private certificates."""
    pass
```

**2. Public Certificate Tests**
```python
def test_issue_public_certificate_letsencrypt():
    """Test issuing public certificate via Let's Encrypt."""
    pass

def test_issue_public_certificate_digicert():
    """Test issuing public certificate via DigiCert."""
    pass

def test_store_public_certificate_in_vault():
    """Test storing public certificate in Vault."""
    pass

def test_tenant_isolation_public():
    """Test tenant isolation for public certificates."""
    pass
```

**3. Integration Tests**
```python
def test_certificate_request_flow():
    """Test complete certificate request flow (UI → API → Provider → Storage)."""
    pass

def test_certificate_renewal_flow():
    """Test certificate renewal flow."""
    pass
```

---

## Implementation Phases

### Phase 1: Provider Abstraction (Week 1)
- [ ] Create base provider interface
- [ ] Implement EJBCA provider
- [ ] Implement Let's Encrypt provider (staging)
- [ ] Add provider selection logic

### Phase 2: Database & Vault Integration (Week 2)
- [ ] Update database schema
- [ ] Implement Vault storage for public certs
- [ ] Add certificate type to models
- [ ] Create public certificate orders table

### Phase 3: API Updates (Week 2-3)
- [ ] Update certificate request endpoint
- [ ] Add provider selection
- [ ] Add Vault storage integration
- [ ] Add billing tracking

### Phase 4: UI Updates (Week 3-4)
- [ ] Add certificate type selection
- [ ] Add provider selection
- [ ] Update certificate list to show type
- [ ] Add cost display

### Phase 5: Testing (Week 4-5)
- [ ] Unit tests for providers
- [ ] Integration tests
- [ ] Tenant isolation tests
- [ ] Vault storage tests

### Phase 6: Production Providers (Week 5-6)
- [ ] Add DigiCert provider
- [ ] Add Sectigo provider (optional)
- [ ] Production Let's Encrypt integration
- [ ] Billing integration

---

## Security Considerations

### Public Certificate Storage
- ✅ Private keys stored in Vault (encrypted)
- ✅ Certificates stored in Vault (tenant-scoped)
- ✅ Access logged and audited
- ✅ No private keys in database

### Provider Credentials
- ✅ API keys stored in Vault
- ✅ Credentials rotated regularly
- ✅ Access restricted to cert_service

### Tenant Isolation
- ✅ Public certificates tenant-scoped in Vault
- ✅ No cross-tenant access
- ✅ Vault policies enforce isolation

---

## Cost Management

### Billing Integration
- Track certificate costs per tenant
- Bill customers for public certificates
- Report costs in admin dashboard

### Cost Tracking
```sql
-- Track costs per tenant
SELECT 
  tenant_id,
  SUM(cost_cents) as total_cost_cents,
  COUNT(*) as certificate_count
FROM certificates
WHERE certificate_type = 'public'
GROUP BY tenant_id;
```

---

## Summary

**Key Features:**
1. ✅ Support for private (EJBCA) and public (paid) certificates
2. ✅ Multiple public certificate providers
3. ✅ Vault storage for public certificates
4. ✅ UI to select certificate type and provider
5. ✅ Admin documentation updates
6. ✅ Comprehensive test suite

**Next Steps:**
1. Review and approve this plan
2. Implement provider abstraction
3. Add Vault storage integration
4. Update UI for certificate type selection
5. Add comprehensive tests

