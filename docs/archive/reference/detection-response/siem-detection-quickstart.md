# SIEM Detection System - Quick Start Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**⏱️ Setup Time:** 15-30 minutes  
**Prerequisites:** OpenSearch cluster, PostgreSQL, Docker Compose

---

## Step 1: Verify OpenSearch Plugins (2 minutes)

```bash
# Check if Alerting plugin is installed
curl 'http://localhost:9200/_cat/plugins?v' -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} | grep alerting

# If not installed:
bin/opensearch-plugin install opensearch-alerting
bin/opensearch-plugin install opensearch-notifications
systemctl restart opensearch
```

Expected output:
```
opensearch-node-1  opensearch-alerting     2.x.x
opensearch-node-1  opensearch-notifications 2.x.x
```

---

## Step 2: Run Database Migrations (1 minute)

```bash
cd backend/migrations

# Run detection rules versioning migration
psql -U sentinelgrid -d sentinelgrid_db -f 023_detection_rules_versioning.sql

# Run traceability audit trail migration
psql -U sentinelgrid -d sentinelgrid_db -f 024_traceability_audit_trail.sql

# Verify tables created
psql -U sentinelgrid -d sentinelgrid_db -c "\dt" | grep detection
```

Expected output:
```
detection_rules
detection_rule_versions
tenant_detection_monitors
detection_rule_executions
detection_playbook_mappings
incident_lifecycle
incident_timeline
... (other tables)
```

---

## Step 3: Deploy Detection Monitors (5 minutes)

```bash
cd backend/services/siem_agent

# Set your tenant ID
export TENANT_ID="550e8400-e29b-41d4-a716-446655440000"

# Deploy all 10 monitors
python scripts/seed_monitors.py seed \
  --tenant-id $TENANT_ID \
  --soar-url http://localhost:8003/api/v1/detection-events/ingest \
  --auth-token your-secret-token

# Verify monitors created
python scripts/seed_monitors.py list --tenant-id $TENANT_ID
```

Expected output:
```
✓ Created webhook destination: dest-abc123
✓ Deployed 10/10 monitors
```

---

## Step 4: Generate Test Data (2 minutes)

```bash
cd backend/tests/siem/data

# Generate test logs for all 10 alert types
python generate_test_logs.py \
  --tenant-id $TENANT_ID \
  --realm sentinelgrid \
  --output-dir ./test_data

# Output: 10 NDJSON files with test logs
```

Expected output:
```
Generated 20 logs for auth_suspicious_login -> test_data/auth_suspicious_login.ndjson
Generated 5 logs for email_phishing_report -> test_data/email_phishing_report.ndjson
...
Total logs generated: 221
```

---

## Step 5: Index Test Data (3 minutes)

```bash
cd test_data

# Helper function to create index header
create_bulk_action() {
  local index=$1
  echo "{\"index\":{\"_index\":\"$index\"}}"
}

# Index auth logs (SG-DET-001, SG-DET-008)
export AUTH_INDEX="sg-$TENANT_ID-auth-$(date +%Y.%m.%d)"
(while IFS= read -r line; do
  create_bulk_action "$AUTH_INDEX"
  echo "$line"
done < auth_suspicious_login.ndjson) | \
curl -X POST 'http://localhost:9200/_bulk' \
  -H 'Content-Type: application/x-ndjson' \
  -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} \
  --data-binary @-

# Index email logs (SG-DET-002, SG-DET-003)
export EMAIL_INDEX="sg-$TENANT_ID-email-$(date +%Y.%m.%d)"
(while IFS= read -r line; do
  create_bulk_action "$EMAIL_INDEX"
  echo "$line"
done < email_phishing_report.ndjson) | \
curl -X POST 'http://localhost:9200/_bulk' \
  -H 'Content-Type: application/x-ndjson' \
  -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} \
  --data-binary @-

# Index endpoint logs (SG-DET-004, SG-DET-005)
export ENDPOINT_INDEX="sg-$TENANT_ID-endpoint-$(date +%Y.%m.%d)"
(while IFS= read -r line; do
  create_bulk_action "$ENDPOINT_INDEX"
  echo "$line"
done < endpoint_malware.ndjson) | \
curl -X POST 'http://localhost:9200/_bulk' \
  -H 'Content-Type: application/x-ndjson' \
  -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} \
  --data-binary @-
```

Verify indexing:
```bash
curl "http://localhost:9200/sg-$TENANT_ID-auth-*/_count" -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD}
curl "http://localhost:9200/sg-$TENANT_ID-email-*/_count" -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD}
curl "http://localhost:9200/sg-$TENANT_ID-endpoint-*/_count" -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD}
```

---

## Step 6: Wait for Monitors to Fire (5-10 minutes)

Monitors run on schedules:
- Auth monitors: Every 5 minutes
- Email monitors: Every 5-10 minutes
- Endpoint monitors: Every 5 minutes
- Other monitors: Every 10-60 minutes

While waiting, monitor logs:
```bash
# Watch SOAR agent logs
docker logs -f soar-agent | grep "detection event"

# Watch for detection events in OpenSearch
watch -n 10 'curl -s "http://localhost:9200/sg-*-detection-*/_count" -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD}'
```

---

## Step 7: Verify Incidents Created (2 minutes)

```bash
# Check incidents in database
psql -U sentinelgrid -d sentinelgrid_db -c "
  SELECT 
    external_id,
    title,
    status as nist_status,
    severity,
    created_at
  FROM incidents
  WHERE tenant_id = '$TENANT_ID'
  ORDER BY created_at DESC
  LIMIT 10;
"

# Check timeline entries
psql -U sentinelgrid -d sentinelgrid_db -c "
  SELECT 
    i.external_id,
    t.timestamp,
    t.event_type,
    t.action,
    t.nist_phase,
    t.nist_status
  FROM incident_timeline t
  JOIN incidents i ON i.id = t.incident_id
  WHERE i.tenant_id = '$TENANT_ID'
  ORDER BY t.timestamp DESC
  LIMIT 10;
"

# Check observables extracted
psql -U sentinelgrid -d sentinelgrid_db -c "
  SELECT 
    i.external_id,
    o.observable_type,
    o.observable_value,
    o.source,
    o.confidence
  FROM incident_observables o
  JOIN incidents i ON i.id = o.incident_id
  WHERE i.tenant_id = '$TENANT_ID'
  ORDER BY o.extracted_at DESC
  LIMIT 20;
"
```

Expected: 3+ incidents created (suspicious login, phishing, malware)

---

## Step 8: View in UI (1 minute)

Open browser to:

1. **Detection Rules Dashboard**
   ```
   http://localhost:3000/dashboard/siem/detection-rules
   ```
   Should show all 10 detection rules with enable/disable status

2. **Detection Events Stream**
   ```
   http://localhost:3000/dashboard/siem/detections
   ```
   Should show fired detection events in real-time

3. **Incidents Dashboard**
   ```
   http://localhost:3000/dashboard/incidents
   ```
   Should show created incidents with NIST status

---

## Troubleshooting

### ❌ Monitors Not Firing

**Symptom:** No detection events after 15 minutes

**Solutions:**
1. Check monitor status:
   ```bash
   curl 'http://localhost:9200/_plugins/_alerting/monitors' -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} | jq '.monitors[] | {id: ._id, name: .name, enabled: .enabled}'
   ```

2. Manually trigger monitor:
   ```bash
   curl -X POST 'http://localhost:9200/_plugins/_alerting/monitors/{monitor_id}/_execute' -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD}
   ```

3. Check data exists:
   ```bash
   curl "http://localhost:9200/sg-$TENANT_ID-auth-*/_search?size=1" -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD}
   ```

### ❌ Webhook Not Received

**Symptom:** Detection events created but no incidents

**Solutions:**
1. Check webhook destination:
   ```bash
   curl 'http://localhost:9200/_plugins/_notifications/configs' -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD}
   ```

2. Check SOAR agent is running:
   ```bash
   curl 'http://localhost:8003/health'
   ```

3. Check SOAR agent logs:
   ```bash
   docker logs soar-agent | grep "detection event"
   ```

### ❌ Incidents Not Created

**Symptom:** Webhook received but no incidents in database

**Solutions:**
1. Check database connection in SOAR agent
2. Verify migrations ran successfully:
   ```bash
   psql -U sentinelgrid -d sentinelgrid_db -c "\dt incident_lifecycle"
   ```
3. Check SOAR agent error logs:
   ```bash
   docker logs soar-agent | grep ERROR
   ```

---

## Testing Individual Alert Types

### Test 1: Suspicious Login (SG-DET-001)

```bash
# Index test data
cd backend/tests/siem/data/test_data
export AUTH_INDEX="sg-$TENANT_ID-auth-$(date +%Y.%m.%d)"

(while IFS= read -r line; do
  echo "{\"index\":{\"_index\":\"$AUTH_INDEX\"}}"
  echo "$line"
done < auth_suspicious_login.ndjson) | \
curl -X POST 'http://localhost:9200/_bulk' \
  -H 'Content-Type: application/x-ndjson' \
  -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} \
  --data-binary @-

# Wait 5 minutes for monitor to run
# Check for detection event and incident
```

Expected: Incident created with `alert_type = suspicious_login`, playbook = `PLAYBOOK_ACCOUNT_TAKEOVER`

### Test 2: User-Reported Phishing (SG-DET-002)

```bash
# Index phishing reports
export EMAIL_INDEX="sg-$TENANT_ID-email-$(date +%Y.%m.%d)"

(while IFS= read -r line; do
  echo "{\"index\":{\"_index\":\"$EMAIL_INDEX\"}}"
  echo "$line"
done < email_phishing_report.ndjson) | \
curl -X POST 'http://localhost:9200/_bulk' \
  -H 'Content-Type: application/x-ndjson' \
  -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} \
  --data-binary @-

# Wait 5 minutes
```

Expected: Incidents created for each phishing report, playbook = `PLAYBOOK_PHISHING_USER_REPORTED`

### Test 3: Endpoint Malware (SG-DET-004)

```bash
# Index malware detections
export ENDPOINT_INDEX="sg-$TENANT_ID-endpoint-$(date +%Y.%m.%d)"

(while IFS= read -r line; do
  echo "{\"index\":{\"_index\":\"$ENDPOINT_INDEX\"}}"
  echo "$line"
done < endpoint_malware.ndjson) | \
curl -X POST 'http://localhost:9200/_bulk' \
  -H 'Content-Type: application/x-ndjson' \
  -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} \
  --data-binary @-

# Wait 5 minutes
```

Expected: Incidents created with `alert_type = endpoint_malware`, observables extracted (file hashes, hosts)

---

## Validation Checklist

After setup, verify:

- [ ] All 10 monitors deployed and enabled
- [ ] Webhook destination created
- [ ] Test data indexed into correct indices
- [ ] Detection events appearing in `sg-{tenant}-detection-*`
- [ ] Incidents created in PostgreSQL
- [ ] Incidents have NIST status = 'new'
- [ ] `incident_lifecycle` records link detection → incident
- [ ] `incident_timeline` has initial entries
- [ ] `incident_observables` contains extracted IOCs
- [ ] Frontend displays detection rules
- [ ] Frontend displays detection events
- [ ] Frontend displays incidents

---

## Daily Operations

### Monitor Health Check

```bash
# Check all monitors for tenant
python backend/services/siem_agent/scripts/seed_monitors.py list \
  --tenant-id $TENANT_ID

# Check recent detection events
curl "http://localhost:9200/sg-$TENANT_ID-detection-*/_search?size=10&sort=@timestamp:desc" -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} | jq '.hits.hits[]._source'

# Check incident creation rate
psql -U sentinelgrid -d sentinelgrid_db -c "
  SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as last_1h
  FROM incidents
  WHERE tenant_id = '$TENANT_ID';
"
```

### Disable Noisy Rule

```bash
# Disable a specific monitor
curl -X PUT "http://localhost:9200/_plugins/_alerting/monitors/{monitor_id}" \
  -H 'Content-Type: application/json' \
  -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} \
  -d '{"enabled": false}'
```

### Update Rule Threshold

```bash
# Update tenant-specific override
psql -U sentinelgrid -d sentinelgrid_db -c "
  UPDATE tenant_detection_monitors
  SET custom_config = jsonb_set(
    COALESCE(custom_config, '{}'::jsonb),
    '{threshold}',
    '10'::jsonb
  )
  WHERE tenant_id = '$TENANT_ID'
  AND rule_id = (SELECT id FROM detection_rules WHERE rule_key = 'SG-DET-001');
"
```

---

## Success Criteria

✅ **Functional End-to-End:**
- Detection → Incident creation works
- Observables extracted automatically
- Timeline entries created
- NIST phases tracked

✅ **Performance:**
- Monitors execute within schedule
- Webhook latency < 5 seconds
- Incident creation < 2 seconds

✅ **Traceability:**
- Every incident traces back to detection event
- Every action logged with timestamp and actor
- Evidence chain of custody maintained

✅ **Multi-Tenant:**
- Tenant isolation verified
- No cross-tenant data leakage
- Correct realm validation

---

## Getting Help

- **Documentation:** `/docs/archive/reference/detection-response/siem-detection-implementation.md`
- **API Reference:** See implementation doc
- **Troubleshooting:** See main doc troubleshooting section

---

**Quick Start Complete!** 🎉

Next: Configure playbook auto-execution and test incident response workflows.

