# SIEM Detection System - Deployment Checklist

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Environment:** Production / Staging / Development  
**Date:** ___________  
**Deployed By:** ___________

---

## Pre-Deployment Checklist

### Infrastructure Requirements

- [ ] OpenSearch cluster running (version 2.x+)
  - [ ] Alerting plugin installed
  - [ ] Notifications plugin installed
  - [ ] Cluster health: Green or Yellow
  - [ ] Sufficient disk space (recommend 500GB+ per tenant)

- [ ] PostgreSQL database (version 13+)
  - [ ] Database: `sentinelgrid_db` created
  - [ ] User with appropriate permissions
  - [ ] Backup configured

- [ ] SIEM Agent service ready
  - [ ] Docker image built
  - [ ] Environment variables configured
  - [ ] OpenSearch connectivity verified

- [ ] SOAR Agent service ready
  - [ ] Docker image built
  - [ ] Environment variables configured
  - [ ] Database connectivity verified

### Configuration Verification

- [ ] Environment variables set:
  ```bash
  # SIEM Agent
  OPENSEARCH_URL=https://opensearch.internal:9200
  OPENSEARCH_USER=sentinelgrid_siem
  OPENSEARCH_PASSWORD=***
  
  # SOAR Agent
  SOAR_AGENT_URL=http://soar-agent:8003
  INTERNAL_SERVICE_TOKEN=***
  DATABASE_URL=postgresql://user:pass@postgres:5432/sentinelgrid_db
  ```

- [ ] Network connectivity:
  - [ ] SIEM Agent → OpenSearch (port 9200)
  - [ ] SOAR Agent → PostgreSQL (port 5432)
  - [ ] OpenSearch → SOAR Agent webhook (HTTP/HTTPS)

---

## Deployment Steps

### Step 1: Database Migrations

```bash
# Connect to PostgreSQL
psql -U sentinelgrid -d sentinelgrid_db

# Run migrations
\i backend/migrations/023_detection_rules_versioning.sql
\i backend/migrations/024_traceability_audit_trail.sql

# Verify tables created
\dt detection_*
\dt incident_*
```

**Verification:**
- [ ] 5 detection tables created
- [ ] 6 incident traceability tables created
- [ ] No SQL errors

### Step 2: Deploy Services

```bash
# Start SIEM Agent
docker-compose up -d siem-agent

# Verify startup
docker logs siem-agent | grep "Index templates configured"

# Start SOAR Agent
docker-compose up -d soar-agent

# Verify startup
docker logs soar-agent | grep "healthy"
```

**Verification:**
- [ ] SIEM Agent responds to `/health`
- [ ] SOAR Agent responds to `/health`
- [ ] OpenSearch templates created
- [ ] No startup errors

### Step 3: Deploy Monitors for Each Tenant

For each tenant:

```bash
export TENANT_ID="<tenant-uuid>"
export TENANT_REALM="<keycloak-realm>"

# Deploy monitors
python backend/services/siem_agent/scripts/seed_monitors.py seed \
  --tenant-id $TENANT_ID \
  --soar-url https://soar.sentinelgrid.internal/api/v1/detection-events/ingest \
  --auth-token $INTERNAL_SERVICE_TOKEN

# Verify
python backend/services/siem_agent/scripts/seed_monitors.py list \
  --tenant-id $TENANT_ID
```

**Verification per tenant:**
- [ ] Webhook destination created
- [ ] 10 monitors deployed
- [ ] All monitors enabled
- [ ] Monitor names include tenant ID prefix

### Step 4: Seed Playbook Mappings

For each tenant:

```bash
python backend/services/soar_agent/app/services/playbook_mapping_loader.py \
  --tenant-id $TENANT_ID
```

**Verification:**
- [ ] 10 playbook mappings created
- [ ] Mappings stored in `detection_playbook_mappings` table
- [ ] Auto-execute configured per requirements

### Step 5: Configure Ingestion Pipeline

```bash
# Deploy Logstash configuration
cp infra/logstash/pipelines/multi-tenant-ingestion.conf \
   /etc/logstash/conf.d/

# Restart Logstash
systemctl restart logstash

# Verify pipeline loaded
curl 'http://localhost:9600/_node/pipelines?pretty'
```

**Verification:**
- [ ] Logstash pipeline loaded
- [ ] No configuration errors
- [ ] Test log ingestion works

---

## Post-Deployment Verification

### Smoke Tests

#### Test 1: Manual Detection Event

```bash
# Send test detection event
curl -X POST 'http://soar-agent:8003/api/v1/detection-events/ingest' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer $INTERNAL_SERVICE_TOKEN' \
  -H 'X-Tenant-ID: $TENANT_ID' \
  -d '{
    "sg": {
      "tenant_id": "'$TENANT_ID'",
      "realm": "'$TENANT_REALM'",
      "alert_type": "suspicious_login",
      "playbook_id": "PLAYBOOK_ACCOUNT_TAKEOVER",
      "severity": "high",
      "category": "identity"
    },
    "rule": {
      "id": "SG-DET-001",
      "name": "Test Detection",
      "version": "1.0.0"
    },
    "user": {
      "id": "test-user",
      "email": "test@example.com"
    }
  }'
```

**Expected:**
- [ ] HTTP 202 Accepted
- [ ] Incident ID returned
- [ ] Incident in database

#### Test 2: Monitor Execution

```bash
# Generate and index test data
cd backend/tests/siem/data
python generate_test_logs.py --tenant-id $TENANT_ID --output-dir ./test_data

# Index auth logs
export AUTH_INDEX="sg-$TENANT_ID-auth-$(date +%Y.%m.%d)"
curl -X POST "http://opensearch:9200/_bulk" \
  -H 'Content-Type: application/x-ndjson' \
  -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} \
  --data-binary @test_data/auth_suspicious_login.ndjson

# Wait 5-10 minutes for monitor to fire
# Check detection events
curl "http://opensearch:9200/sg-$TENANT_ID-detection-*/_search?size=5&sort=@timestamp:desc" -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD}
```

**Expected:**
- [ ] Test data indexed successfully
- [ ] Monitor fires within schedule window
- [ ] Detection event created
- [ ] Incident created

#### Test 3: End-to-End Traceability

```bash
# Get recent incident
INCIDENT_ID=$(psql -U sentinelgrid -d sentinelgrid_db -t -c "
  SELECT id FROM incidents 
  WHERE tenant_id = '$TENANT_ID' 
  ORDER BY created_at DESC LIMIT 1;
" | tr -d ' ')

# Verify traceability chain
psql -U sentinelgrid -d sentinelgrid_db -c "
  SELECT 
    'Incident' as entity,
    i.external_id as id,
    i.status,
    i.created_at
  FROM incidents i
  WHERE i.id = '$INCIDENT_ID'
  
  UNION ALL
  
  SELECT 
    'Lifecycle' as entity,
    l.detection_event_id as id,
    NULL as status,
    l.created_at
  FROM incident_lifecycle l
  WHERE l.incident_id = '$INCIDENT_ID'
  
  UNION ALL
  
  SELECT 
    'Timeline' as entity,
    t.action as id,
    t.nist_status as status,
    t.timestamp as created_at
  FROM incident_timeline t
  WHERE t.incident_id = '$INCIDENT_ID'
  ORDER BY created_at;
"
```

**Expected:**
- [ ] Incident record exists
- [ ] Lifecycle record links to detection event
- [ ] Timeline has initial "detected" entry
- [ ] All timestamps consistent

---

## Monitoring & Alerting Setup

### Key Metrics to Monitor

1. **Monitor Health**
   ```bash
   # Check monitor execution failures
   curl 'http://opensearch:9200/_plugins/_alerting/monitors/_search?size=100' -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} | \
     jq '.monitors[] | select(.enabled == true) | {id: .id, name: .name, last_run: .last_run_time}'
   ```

2. **Detection Event Rate**
   ```bash
   # Events per hour
   curl "http://opensearch:9200/sg-*-detection-*/_search" -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} -d '{
     "size": 0,
     "query": {"range": {"@timestamp": {"gte": "now-1h"}}},
     "aggs": {"by_tenant": {"terms": {"field": "sg.tenant_id"}}}
   }'
   ```

3. **Incident Creation Rate**
   ```sql
   SELECT 
     DATE_TRUNC('hour', created_at) as hour,
     COUNT(*) as incidents
   FROM incidents
   WHERE created_at > NOW() - INTERVAL '24 hours'
   GROUP BY DATE_TRUNC('hour', created_at)
   ORDER BY hour DESC;
   ```

4. **Webhook Failures**
   ```bash
   # Check SOAR agent logs for webhook errors
   docker logs soar-agent --since 1h | grep -i "error.*detection"
   ```

### Alert Thresholds

- [ ] Alert if monitor hasn't run in 2x schedule interval
- [ ] Alert if webhook failure rate > 5%
- [ ] Alert if incident creation fails
- [ ] Alert if disk space < 20%

---

## Rollback Procedure

If deployment fails:

1. **Disable All Monitors**
   ```bash
   python backend/services/siem_agent/scripts/seed_monitors.py delete \
     --tenant-id $TENANT_ID \
     --confirm
   ```

2. **Rollback Database Migrations**
   ```bash
   psql -U sentinelgrid -d sentinelgrid_db -c "
     DROP TABLE IF EXISTS incident_evidence CASCADE;
     DROP TABLE IF EXISTS incident_observables CASCADE;
     DROP TABLE IF EXISTS incident_actions CASCADE;
     DROP TABLE IF EXISTS playbook_execution_audit CASCADE;
     DROP TABLE IF EXISTS incident_timeline CASCADE;
     DROP TABLE IF EXISTS incident_lifecycle CASCADE;
     DROP TABLE IF EXISTS detection_playbook_mappings CASCADE;
     DROP TABLE IF EXISTS detection_rule_executions CASCADE;
     DROP TABLE IF EXISTS tenant_detection_monitors CASCADE;
     DROP TABLE IF EXISTS detection_rule_versions CASCADE;
     DROP TABLE IF EXISTS detection_rules CASCADE;
   "
   ```

3. **Stop Services**
   ```bash
   docker-compose stop siem-agent soar-agent
   ```

---

## Post-Deployment Tasks

### Day 1
- [ ] Monitor all 10 detection rules for false positives
- [ ] Review incident creation rate
- [ ] Verify webhook delivery success rate
- [ ] Check database growth rate

### Week 1
- [ ] Review incident response times
- [ ] Analyze false positive rate per rule
- [ ] Tune thresholds if needed
- [ ] Verify playbook execution success rate

### Month 1
- [ ] Generate compliance report
- [ ] Review NIST phase progression times
- [ ] Analyze most common alert types
- [ ] Plan rule optimizations

---

## Success Criteria

✅ **Functional:**
- All monitors firing on schedule
- Incidents created within 30 seconds of detection
- Traceability verified for all incidents
- No webhook failures

✅ **Performance:**
- Detection event ingestion < 1 second
- Incident creation < 2 seconds
- Database query performance acceptable
- OpenSearch cluster healthy

✅ **Compliance:**
- NIST phases tracked correctly
- Audit trail complete
- Observable provenance maintained
- Evidence chain of custody working

✅ **Operational:**
- UI accessible and functional
- Monitoring and alerting configured
- Documentation accessible
- Team trained on new system

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Security Engineer | _________ | _________ | _____ |
| DevOps Engineer | _________ | _________ | _____ |
| SOC Manager | _________ | _________ | _____ |
| Platform Owner | _________ | _________ | _____ |

---

**Deployment Status:** ⬜ Planning  ⬜ In Progress  ⬜ Complete  ⬜ Verified

**Notes:**

_______________________________________________
_______________________________________________
_______________________________________________

