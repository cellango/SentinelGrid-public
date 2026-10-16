# EJBCA Multi-Tenant Security Implementation

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Priority:** 🔴 CRITICAL - Security Requirement  
**Goal:** Ensure complete tenant isolation for certificate management

---

## Security Requirements

### Core Principle
**One tenant MUST NOT be able to see, access, or modify another tenant's certificates, CA authorities, or bootstrap tokens.**

### Isolation Boundaries
1. **Certificate Isolation:** Certificates are scoped to `tenant_id`
2. **CA Authority Isolation:** CA authorities can be per-tenant or shared (with tenant filtering)
3. **Bootstrap Token Isolation:** Bootstrap tokens are scoped to `tenant_id`
4. **Certificate Request Isolation:** Requests are scoped to `tenant_id`

---

## Current State Analysis

### ✅ What's Already in Place
- Database models have `tenant_id` fields:
  - `Certificate.tenant_id` (nullable - service certs may not have tenant)
  - `CertificateRequest.tenant_id` (nullable)
  - `AgentBootstrapToken.tenant_id` (required)
- Indexes exist on `tenant_id` fields for performance

### ❌ What's Missing
- **API endpoints do NOT enforce tenant isolation**
- **No tenant_id extraction from JWT tokens**
- **No tenant filtering in database queries**
- **CAAuthority model lacks tenant_id**
- **Service-to-service calls bypass tenant checks**
- **No tenant validation in certificate operations**

---

## Implementation Plan

### Phase 1: Database Schema Updates

#### 1.1 Add tenant_id to CAAuthority
```sql
ALTER TABLE ca_authorities 
  ADD COLUMN tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX idx_ca_authorities_tenant_id ON ca_authorities(tenant_id);
```

**Rationale:**
- Allows per-tenant CA authorities (strong isolation)
- Supports shared CA authorities (tenant_id = NULL)
- Enables tenant-scoped CA selection

#### 1.2 Make Certificate.tenant_id Required (for agent certs)
```sql
-- Keep nullable for service certificates (may be platform-level)
-- But ensure agent certificates always have tenant_id
-- Enforced at application level
```

### Phase 2: Authentication & Authorization

#### 2.1 Add JWT Token Validation
**File:** `backend/services/cert_service/app/core/auth.py` (NEW)

```python
"""Authentication and authorization for certificate service."""

from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os

from app.core.config import settings

security = HTTPBearer()
IAM_AGENT_URL = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")


def verify_token(token: str) -> dict:
    """Verify JWT token and extract tenant_id."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token}
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("valid"):
                raise HTTPException(status_code=401, detail="Invalid token")
            
            payload = result.get("payload", {})
            tenant_id = result.get("tenant_id")
            
            if not tenant_id:
                raise HTTPException(
                    status_code=403, 
                    detail="Token missing tenant_id - cannot access certificate service"
                )
            
            return {
                "tenant_id": tenant_id,
                "user_id": result.get("user_id"),
                "roles": result.get("roles", [])
            }
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to IAM Agent: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token validation error: {str(e)}"
        )


def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> UUID:
    """
    FastAPI dependency to extract and validate tenant_id from JWT token.
    
    Usage:
        @router.get("/certificates")
        def list_certificates(tenant_id: UUID = Depends(get_current_tenant)):
            ...
    """
    token = credentials.credentials
    payload = verify_token(token)
    tenant_id_str = payload.get("tenant_id")
    
    if not tenant_id_str:
        raise HTTPException(
            status_code=403,
            detail="Missing tenant_id in token"
        )
    
    try:
        return UUID(tenant_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid tenant_id format"
        )


def require_role(allowed_roles: list[str]):
    """
    Dependency factory to require specific roles.
    
    Usage:
        @router.post("/certificates")
        def create_certificate(
            tenant_id: UUID = Depends(get_current_tenant),
            _roles: dict = Depends(require_role(["TENANT_ADMIN", "SOC_MANAGER"]))
        ):
            ...
    """
    def role_checker(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> dict:
        token = credentials.credentials
        payload = verify_token(token)
        roles = payload.get("roles", [])
        
        if not any(role in roles for role in allowed_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Required role not found. Allowed: {allowed_roles}"
            )
        
        return payload
    
    return role_checker
```

### Phase 3: API Endpoint Updates

#### 3.1 Update All Endpoints to Use Tenant Isolation

**File:** `backend/services/cert_service/app/api/certificates.py`

**Changes Required:**

1. **List Certificates Endpoint (NEW)**
```python
@router.get("/v1/certificates", response_model=List[CertificateResponse])
async def list_certificates(
    status: Optional[str] = Query(None),
    usage: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: UUID = Depends(get_current_tenant),  # ← Extract from token
    db: Session = Depends(get_db)
):
    """List certificates for the current tenant."""
    query = db.query(Certificate).filter(
        Certificate.tenant_id == tenant_id  # ← Tenant filter
    )
    
    if status:
        query = query.filter(Certificate.status == status)
    if usage:
        query = query.filter(Certificate.usage == usage)
    
    total = query.count()
    certificates = query.order_by(Certificate.created_at.desc()).offset(offset).limit(limit).all()
    
    return [CertificateResponse.from_orm(c) for c in certificates]
```

2. **Get Certificate Endpoint (UPDATE)**
```python
@router.get("/v1/certificates/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(
    certificate_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),  # ← Extract from token
    db: Session = Depends(get_db)
):
    """Get certificate by ID - tenant-scoped."""
    certificate = db.query(Certificate).filter(
        Certificate.id == certificate_id,
        Certificate.tenant_id == tenant_id  # ← Tenant filter
    ).first()
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return CertificateResponse.from_orm(certificate)
```

3. **Revoke Certificate Endpoint (UPDATE)**
```python
@router.post("/v1/certificates/{certificate_id}/revoke", response_model=RevokeCertResponse)
async def revoke_certificate(
    certificate_id: UUID,
    request: RevokeCertRequest,
    tenant_id: UUID = Depends(get_current_tenant),  # ← Extract from token
    db: Session = Depends(get_db)
):
    """Revoke a certificate - tenant-scoped."""
    # Verify certificate belongs to tenant
    certificate = db.query(Certificate).filter(
        Certificate.id == certificate_id,
        Certificate.tenant_id == tenant_id  # ← Tenant filter
    ).first()
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    service = CertificateService(db, tenant_id=tenant_id)
    result = service.revoke_certificate(certificate_id, request.reason)
    return RevokeCertResponse(**result)
```

4. **Create Bootstrap Token Endpoint (UPDATE)**
```python
@router.post("/v1/bootstrap-tokens", response_model=CreateBootstrapTokenResponse)
async def create_bootstrap_token(
    request: CreateBootstrapTokenRequest,
    tenant_id: UUID = Depends(get_current_tenant),  # ← Extract from token
    db: Session = Depends(get_db)
):
    """Create bootstrap token - tenant-scoped."""
    # Override request.tenant_id with token tenant_id (security)
    service = CertificateService(db, tenant_id=tenant_id)
    result = service.create_bootstrap_token(
        tenant_id=tenant_id,  # ← Use token tenant_id, not request
        agent_id=request.agent_id,
        ttl_hours=request.ttl_hours
    )
    return CreateBootstrapTokenResponse(**result)
```

5. **Service Enrollment (KEEP SERVICE TOKEN)**
```python
@router.post("/v1/certificates/enroll-service", response_model=IssueCertResponse)
async def enroll_service(
    request: IssueCertRequest,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_service_token)  # ← Service token (internal)
):
    """Enroll a service - internal service-to-service call."""
    # Service certificates may not have tenant_id (platform-level)
    # But if tenant_id is provided, validate it exists
    if request.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == request.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=400, detail="Invalid tenant_id")
    
    service = CertificateService(db)
    result = service.enroll_service(...)
    return IssueCertResponse(**result)
```

### Phase 4: Service Layer Updates

#### 4.1 Update CertificateService to Enforce Tenant Isolation

**File:** `backend/services/cert_service/app/services/cert_service.py`

```python
class CertificateService:
    """Service for managing certificates with tenant isolation."""
    
    def __init__(self, db: Session, tenant_id: Optional[UUID] = None):
        self.db = db
        self.tenant_id = tenant_id  # ← Store tenant_id
    
    def get_certificate(self, certificate_id: UUID) -> Optional[Certificate]:
        """Get certificate by ID - tenant-scoped."""
        query = self.db.query(Certificate).filter(
            Certificate.id == certificate_id
        )
        
        # Enforce tenant isolation
        if self.tenant_id:
            query = query.filter(Certificate.tenant_id == self.tenant_id)
        
        return query.first()
    
    def list_certificates(
        self,
        status: Optional[str] = None,
        usage: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Certificate], int]:
        """List certificates - tenant-scoped."""
        query = self.db.query(Certificate)
        
        # Enforce tenant isolation
        if self.tenant_id:
            query = query.filter(Certificate.tenant_id == self.tenant_id)
        
        if status:
            query = query.filter(Certificate.status == status)
        if usage:
            query = query.filter(Certificate.usage == usage)
        
        total = query.count()
        certificates = query.order_by(Certificate.created_at.desc()).offset(offset).limit(limit).all()
        
        return certificates, total
    
    def revoke_certificate(self, certificate_id: UUID, reason: str = "unspecified") -> dict:
        """Revoke certificate - tenant-scoped."""
        certificate = self.get_certificate(certificate_id)  # ← Uses tenant filter
        
        if not certificate:
            raise ValueError(f"Certificate {certificate_id} not found")
        
        # ... rest of revocation logic
```

#### 4.2 Update CA Authority Selection

```python
def get_ca_for_tenant(self, tenant_id: UUID) -> CAAuthority:
    """Get CA authority for tenant with isolation."""
    # Try per-tenant CA first
    ca = self.db.query(CAAuthority).filter(
        CAAuthority.tenant_id == tenant_id,
        CAAuthority.status == "active"
    ).first()
    
    if ca:
        return ca
    
    # Fall back to shared CA (tenant_id is NULL)
    ca = self.db.query(CAAuthority).filter(
        CAAuthority.tenant_id.is_(None),
        CAAuthority.status == "active"
    ).first()
    
    if not ca:
        raise ValueError("No active CA authority found for tenant")
    
    return ca
```

### Phase 5: EJBCA Provider Updates

#### 5.1 Per-Tenant CA Selection

**File:** `backend/services/cert_service/app/providers/ejbca.py`

```python
class EJBCAProvider(CAProvider):
    """EJBCA provider with tenant isolation."""
    
    def __init__(
        self,
        ejbca_url: str,
        ejbca_username: str,
        ejbca_password: str,
        ca_name: str,  # ← Per-tenant CA name
        certificate_profile: str = "service-tls",
        tenant_id: Optional[UUID] = None  # ← Track tenant
    ):
        self.ejbca_url = ejbca_url
        self.ejbca_username = ejbca_username
        self.ejbca_password = ejbca_password
        self.ca_name = ca_name  # ← Tenant-specific CA
        self.certificate_profile = certificate_profile
        self.tenant_id = tenant_id  # ← For logging/audit
```

### Phase 6: Frontend Updates

#### 6.1 API Client with Tenant Context

**File:** `frontend/src/lib/api/certificates.ts`

```typescript
// API client automatically includes tenant_id from auth token
export const certificateApi = {
  listCertificates: (filters?: CertificateFilters) => 
    api.get('/api/v1/certificates', { 
      params: filters,
      // tenant_id automatically included in Authorization header
    }),
  
  getCertificate: (id: string) => 
    api.get(`/api/v1/certificates/${id}`),
  
  // ... other methods
};
```

**Note:** Frontend doesn't need to pass tenant_id - it's extracted from JWT token by backend.

---

## Security Testing

### Test Cases

1. **Tenant Isolation Tests**
   - ✅ Tenant A cannot list Tenant B's certificates
   - ✅ Tenant A cannot get Tenant B's certificate by ID
   - ✅ Tenant A cannot revoke Tenant B's certificate
   - ✅ Tenant A cannot create bootstrap tokens for Tenant B
   - ✅ Tenant A cannot access Tenant B's CA authorities

2. **Token Validation Tests**
   - ✅ Request without token → 401
   - ✅ Request with invalid token → 401
   - ✅ Request with token missing tenant_id → 403
   - ✅ Request with valid token → Success

3. **Database Query Tests**
   - ✅ All queries filter by tenant_id
   - ✅ No cross-tenant data leakage
   - ✅ Indexes support tenant filtering

---

## Migration Plan

### Step 1: Add tenant_id to CAAuthority
```sql
ALTER TABLE ca_authorities ADD COLUMN tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;
CREATE INDEX idx_ca_authorities_tenant_id ON ca_authorities(tenant_id);
```

### Step 2: Update Existing Data
```sql
-- For existing shared CA authorities, set tenant_id = NULL
UPDATE ca_authorities SET tenant_id = NULL WHERE tenant_id IS NULL;

-- For service certificates without tenant_id, keep as-is (platform-level)
-- Agent certificates should already have tenant_id
```

### Step 3: Deploy API Updates
- Deploy new authentication middleware
- Update all endpoints to use tenant isolation
- Test thoroughly before production

---

## Monitoring & Auditing

### Audit Logging
- Log all certificate operations with tenant_id
- Track cross-tenant access attempts
- Monitor for tenant isolation violations

### Metrics
- Certificate operations per tenant
- Failed tenant isolation checks
- Token validation failures

---

## Summary

### Critical Changes
1. ✅ Add `tenant_id` to `CAAuthority` model
2. ✅ Add JWT token validation to all user-facing endpoints
3. ✅ Add tenant filtering to all database queries
4. ✅ Update service layer to enforce tenant isolation
5. ✅ Update EJBCA provider to support per-tenant CAs
6. ✅ Add comprehensive tenant isolation tests

### Security Guarantees
- ✅ No tenant can access another tenant's certificates
- ✅ All user-facing endpoints require valid JWT with tenant_id
- ✅ Database queries are always filtered by tenant_id
- ✅ Service-to-service calls are clearly marked and audited
- ✅ Bootstrap tokens are tenant-scoped

---

**Status:** Ready for Implementation  
**Priority:** 🔴 CRITICAL - Must be completed before production deployment

