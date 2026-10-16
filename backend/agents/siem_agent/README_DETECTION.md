# SentinelGrid SIEM Detection System

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


**Version:** 1.0.0  
**Status:** ✅ Production Ready  
**NIST Alignment:** SP 800-61 Rev 2

---

## Overview

Complete SIEM detection system with 10 OpenSearch monitors that automatically create NIST-compliant incidents in the SOAR platform with 100% traceability.

### Key Features

- ✅ **10 Detection Rules** - Identity, Email, Endpoint, Cloud, Network, Device
- ✅ **Multi-Tenant** - Complete isolation with sg.tenant_id and sg.realm
- ✅ **Versioned Rules** - Semantic versioning with rollback capability
- ✅ **100% Traceability** - Complete audit trail from detection to resolution
- ✅ **NIST Compliant** - SP 800-61 IR phases and status tracking
- ✅ **Auto-Playbooks** - Configurable automated response
- ✅ **Real-time Webhooks** - OpenSearch → SOAR integration

---

## Quick Start

### 1. Prerequisites

```bash
# Verify OpenSearch plugins
curl 'http://localhost:9200/_cat/plugins?v' -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} | grep -E 'alerting|notifications'

# Run database migrations
psql -U sentinelgrid -d sentinelgrid_db -f backend/migrations/023_detection_rules_versioning.sql
psql -U sentinelgrid -d sentinelgrid_db -f backend/migrations/024_traceability_audit_trail.sql
```

### 2. Deploy Monitors

```bash
cd backend/agents/siem_agent

export TENANT_ID="your-tenant-uuid"

python scripts/seed_monitors.py seed --tenant-id $TENANT_ID
```

### 3. Seed Playbook Mappings

```bash
cd backend/agents/soar_agent

python app/services/playbook_mapping_loader.py --tenant-id $TENANT_ID
```

### 4. Generate Test Data

```bash
cd backend/tests/siem/data

python generate_test_logs.py --tenant-id $TENANT_ID --output-dir ./test_data
```

### 5. Verify

```bash
# Check monitors
python backend/agents/siem_agent/scripts/seed_monitors.py list --tenant-id $TENANT_ID

# Check incidents (after monitors fire)
psql -U sentinelgrid -d sentinelgrid_db -c "
  SELECT external_id, title, status, severity FROM incidents 
  WHERE tenant_id = '$TENANT_ID' ORDER BY created_at DESC LIMIT 5;
"
```

**Full setup time:** 15-30 minutes

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    OpenSearch                            │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Logs: sg-{tenant}-{type}-YYYY.MM.DD               │ │
│  │  - auth-*, email-*, endpoint-*, cloud-*, ...       │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  10 Detection Monitors (per tenant)                │ │
│  │  - Query, aggregate, evaluate triggers             │ │
│  │  - Run every 5-60 minutes                          │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Detection Events: sg-{tenant}-detection-*         │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         ↓ Webhook
┌─────────────────────────────────────────────────────────┐
│              SOAR Agent (Incident Creator)               │
│  1. Validate tenant context                             │
│  2. Create incident (NIST status: NEW)                  │
│  3. Create lifecycle & timeline records                  │
│  4. Extract observables (IOCs)                          │
│  5. Trigger playbook (if auto_execute=true)             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                    │
│  - incidents (NIST status, severity)                    │
│  - incident_lifecycle (detection → incident)             │
│  - incident_timeline (every action logged)              │
│  - incident_observables (IOCs with provenance)          │
│  - incident_actions (before/after snapshots)            │
│  - playbook_execution_audit (node-level trace)          │
└─────────────────────────────────────────────────────────┘
```

---

## 10 Detection Rules

| Rule | Threat | Schedule | Threshold | Auto-Execute |
|------|--------|----------|-----------|--------------|
| SG-DET-001 | Suspicious Login | 5 min | ≥5 fails + 1 success | ❌ |
| SG-DET-002 | User-Reported Phishing | 5 min | Any report | ✅ |
| SG-DET-003 | Phishing Campaign | 10 min | High/Critical | ✅ |
| SG-DET-004 | Endpoint Malware | 5 min | High/Critical | ✅ |
| SG-DET-005 | Ransomware | 5 min | Any ransomware | ✅ |
| SG-DET-006 | Public S3 Bucket | 15 min | Public access | ✅ |
| SG-DET-007 | Privilege Escalation | 10 min | Admin role grant | ❌ |
| SG-DET-008 | Password Spray | 10 min | ≥50 fails, ≥10 users | ✅ |
| SG-DET-009 | Data Exfiltration | 60 min | >10GB in 1h | ❌ |
| SG-DET-010 | Lost Device | 15 min | Status=lost/stolen | ✅ |

---

## Documentation

- **[Implementation Guide](../../../docs/archive/reference/detection-response/siem-detection-implementation.md)** - Complete technical reference
- **[Quick Start](../../../docs/archive/reference/detection-response/siem-detection-quickstart.md)** - 30-minute setup
- **[Deployment Checklist](../../../docs/archive/reference/detection-response/siem-detection-deployment-checklist.md)** - Production deployment
- **[Summary](../../../docs/archive/README.md#retired-references)** - Overview and metrics

---

## Scripts

### Monitor Management

```bash
# Deploy monitors for tenant
python scripts/seed_monitors.py seed --tenant-id <UUID>

# List monitors
python scripts/seed_monitors.py list --tenant-id <UUID>

# Delete monitors
python scripts/seed_monitors.py delete --tenant-id <UUID> --confirm
```

### Test Data Generation

```bash
# Generate logs for all 10 alert types
cd ../../tests/siem/data
python generate_test_logs.py --tenant-id <UUID> --output-dir ./test_data
```

### Playbook Mapping

```bash
# Seed playbook mappings
cd ../../../soar_agent
python app/services/playbook_mapping_loader.py --tenant-id <UUID>
```

---

## API Endpoints

### SIEM Agent (Detection Events)

```
POST /detection/events              # Ingest detection event
GET  /detection/events              # Search events
GET  /detection/events/{id}         # Get specific event
GET  /detection/stats               # Statistics
```

### SOAR Agent (Webhook)

```
POST /api/v1/detection-events/ingest   # Webhook receiver (OpenSearch)
GET  /api/v1/detection-events/health   # Health check
```

---

## Database Schema

### Core Tables (Migration 023)
- `detection_rules` - Rule catalog
- `detection_rule_versions` - Version history
- `tenant_detection_monitors` - Deployment tracking
- `detection_rule_executions` - Execution audit
- `detection_playbook_mappings` - Alert → playbook mapping

### Traceability Tables (Migration 024)
- `incident_lifecycle` - Detection → incident linkage
- `incident_timeline` - Complete action log
- `playbook_execution_audit` - Playbook trace
- `incident_actions` - Actions with before/after state
- `incident_observables` - IOCs with provenance
- `incident_evidence` - Chain of custody

---

## Configuration Files

- `app/config/monitor_definitions.py` - 10 detection rule definitions
- `app/config/ingest_pipelines.yaml` - OpenSearch ingest pipelines
- `../soar_agent/app/config/alert_playbook_mapping.yaml` - Playbook mappings

---

## Testing

```bash
# Run unit tests
cd backend/tests/siem
pytest test_detection_monitors.py -v

# Test all 10 alert types
pytest test_detection_monitors.py -v -k test_suspicious_login
pytest test_detection_monitors.py -v -k test_user_reported_phishing
# ... etc
```

---

## Troubleshooting

**Problem:** Monitors not firing  
**Solution:** Check data exists, verify tenant_id in logs, manually trigger monitor

**Problem:** Webhook not received  
**Solution:** Check destination config, verify SOAR agent running, check network connectivity

**Problem:** Incidents not created  
**Solution:** Check database migrations, verify tenant exists, check SOAR logs

See [Implementation Guide](../../../docs/archive/reference/detection-response/siem-detection-implementation.md#troubleshooting) for detailed troubleshooting.

---

## Support

- **Documentation:** `/docs/SIEM_DETECTION_*.md`
- **Issues:** GitHub Issues
- **Team:** Security Engineering

---

**Ready to deploy!** 🚀

