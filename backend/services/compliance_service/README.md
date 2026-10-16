# SentinelGrid Compliance Service

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


AI-powered compliance management platform with SOC 2, NIST CSF, HIPAA, PCI DSS, and CMMC support.

---

## Overview

The Compliance Service provides:

- **Control Library**: SOC 2, NIST CSF, HIPAA, PCI DSS, CMMC
- **Compliance Mapping**: SentinelGrid features → compliance controls
- **Evidence Collection**: Automated evidence gathering for audits
- **Gap Analysis**: Identify controls needing attention
- **Assessment Tracking**: Per-tenant compliance status

---

## Features

### Compliance Frameworks

- ✅ **SOC 2 Trust Services Criteria** (2017) - Security, Availability, Confidentiality
- ✅ **NIST Cybersecurity Framework** (1.1) - 5 functions (Identify, Protect, Detect, Respond, Recover)
- ✅ **HIPAA Security Rule** (2013) - Administrative & Technical Safeguards
- ✅ **PCI DSS** (4.0) - Payment card data security
- ✅ **CMMC / NIST 800-171** (2.0) - Federal contractor requirements

### Control Library

Pre-loaded with controls from all frameworks:
- SOC 2: 11 key controls (CC6.x, CC7.x, CC8.x)
- NIST CSF: 23 subcategories across 5 functions
- HIPAA: 12 Security Rule controls
- PCI DSS: 15 requirements mapped
- CMMC: 110 Level 2 practices

### Evidence Collection

Automated collection from:
- IAM Agent (access reviews, MFA status, user management)
- SIEM Agent (log coverage, retention policies)
- SOAR Agent (incident response, playbook execution)
- Posture Agent (cloud misconfigurations, CIS findings)
- Audit Service (platform audit logs)

---

## API Endpoints

### Control Library

```
GET  /api/v1/compliance/frameworks              # List frameworks
GET  /api/v1/compliance/frameworks/{id}/controls # List controls
GET  /api/v1/compliance/controls/{id}           # Control details
POST /api/v1/compliance/controls/{id}/mapping   # Map to feature
```

### Tenant Status

```
GET  /api/v1/compliance/status/{tenant_id}      # Overall status
GET  /api/v1/compliance/controls/{id}/status    # Control status
PUT  /api/v1/compliance/controls/{id}/status    # Update status
```

### Evidence

```
POST /api/v1/compliance/evidence/collect        # Collect evidence
GET  /api/v1/compliance/evidence/packages       # List packages
POST /api/v1/compliance/evidence/packages/{id}/export # Export
```

### Dashboard

```
GET  /api/v1/compliance/dashboard               # Dashboard data
GET  /api/v1/compliance/gap-analysis            # Gap analysis
```

---

## Database Schema

### Tables Created (Migration 030)

1. `compliance_frameworks` - Framework definitions
2. `compliance_controls` - Individual controls
3. `control_mappings` - Feature-to-control mappings
4. `tenant_control_status` - Per-tenant implementation status

### Example Control Mapping

```sql
-- Example: SOC 2 CC6.6 (MFA) mapped to SentinelGrid MFA enforcement
INSERT INTO control_mappings (control_id, sentinelgrid_feature, coverage_level, evidence_sources)
VALUES (
    (SELECT id FROM compliance_controls WHERE control_id = 'CC6.6'),
    'mfa_enforcement_policies',
    'full',
    ARRAY['mfa_dashboard', 'user_mfa_status', 'mfa_compliance_violations']
);
```

---

## Control Data Files

Located in `app/data/`:

1. **soc2_controls.json** - SOC 2 Trust Services Criteria
2. **hipaa_security_rule.json** - HIPAA Administrative & Technical Safeguards
3. **pci_dss_requirements.json** - PCI DSS v4.0 Requirements
4. **nist_800_171_controls.json** - NIST 800-171 Rev 2 + CMMC Level 2

### JSON Structure

```json
{
  "framework": "SOC2",
  "version": "2017",
  "categories": [
    {
      "code": "CC6",
      "name": "Logical and Physical Access Controls",
      "controls": [
        {
          "control_id": "CC6.1",
          "control_name": "Logical and physical access controls",
          "description": "...",
          "priority": "critical",
          "sentinelgrid_features": ["iam_agent", "rbac"],
          "coverage_level": "full"
        }
      ]
    }
  ]
}
```

---

## Integration with Other Services

### IAM Agent Integration

```python
# Collect IAM evidence
from app.services.evidence_collector import collect_iam_evidence

evidence = collect_iam_evidence(
    tenant_id=tenant_id,
    controls=['CC6.1', 'CC6.2', 'CC6.3']
)
# Returns: access reviews, MFA status, user lifecycle logs
```

### Reporting Service Integration

```python
# Generate SOC 2 report with control data
from app.services.control_mapper import get_soc2_coverage

coverage = get_soc2_coverage(tenant_id=tenant_id)
# Returns: control status, evidence links, gap analysis
```

---

## Usage Examples

### Check SOC 2 Compliance Status

```python
import requests

response = requests.get(
    'https://api.sentinelgrid.io/api/v1/compliance/status/tenant-uuid',
    headers={'Authorization': f'Bearer {token}'},
    params={'framework': 'SOC2'}
)

status = response.json()
print(f"SOC 2 Coverage: {status['coverage_percentage']}%")
print(f"Controls Implemented: {status['controls_implemented']}/{status['total_controls']}")
```

### Collect Evidence for Audit

```python
response = requests.post(
    'https://api.sentinelgrid.io/api/v1/compliance/evidence/collect',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'framework': 'SOC2',
        'period_start': '2025-01-01',
        'period_end': '2025-12-31',
        'controls': ['CC6.1', 'CC6.2', 'CC6.3', 'CC7.2']
    }
)

package = response.json()
print(f"Evidence Package ID: {package['package_id']}")
print(f"Evidence Items: {package['items_count']}")
```

---

## Configuration

### Environment Variables

```bash
# Service configuration
SERVICE_NAME=compliance-service
VERSION=1.0.0
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/sentinelgrid

# Evidence storage
EVIDENCE_STORAGE_PATH=/var/sentinelgrid/evidence
S3_EVIDENCE_BUCKET=sentinelgrid-evidence

# Integration endpoints
IAM_AGENT_URL=http://iam-agent:8000
SIEM_AGENT_URL=http://siem-agent:8000
SOAR_AGENT_URL=http://soar-agent:8000
POSTURE_AGENT_URL=http://posture-agent:8000
```

---

## Development

### Running Locally

```bash
cd backend/services/compliance_service

# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn app.main:app --reload --port 8000

# Service available at http://localhost:8000
```

### Running Tests

```bash
pytest tests/ -v
```

---

## Deployment

### Docker

```bash
docker build -t sentinelgrid/compliance-service .
docker run -d \
  --name compliance-service \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  sentinelgrid/compliance-service
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-service
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: compliance-service
        image: sentinelgrid/compliance-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
```

---

## Support

For issues or questions:
- Documentation: `docs/archive/reference/platform/compliance-platform-guide.md`
- API Reference: `docs/archive/reference/development/compliance-api-reference.md`
- Deployment: `docs/archive/reference/infrastructure/compliance-deployment-quickstart.md`

---

**Version:** 1.0.0  
**Last Updated:** December 2, 2025  
**Status:** ✅ Production Ready

