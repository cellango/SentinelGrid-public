# Detection Event Deduplication & Suppression Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Date:** December 2, 2025  
**Status:** ✅ Implemented

---

## Overview

The deduplication and suppression system prevents alert fatigue by:
1. **Deduplicating similar events** - Same user + same issue = 1 incident
2. **Suppressing within time windows** - Prevent repeated incidents
3. **Escalating after thresholds** - Create new incident if problem persists
4. **Maintaining audit trail** - All suppressions logged

---

## How It Works

### Deduplication Logic

```
Detection Event arrives
  ↓
Extract dedup fields (user.id, source.ip, host.name, etc.)
  ↓
Generate dedup_key (SHA-256 hash of fields)
  ↓
Check if dedup_key exists in last N minutes
  ↓
  ├─ Not found → Create incident + dedup record
  └─ Found → Update occurrence_count
      ↓
      Check suppression rules
        ↓
        ├─ Should suppress → Log suppression, link to original incident
        └─ Should escalate → Create new incident
```

### Deduplication Keys by Alert Type

| Alert Type | Dedup Fields | Time Window | Rationale |
|------------|--------------|-------------|-----------|
| suspicious_login | user.id + source.ip | 60 min | Same user from same IP |
| phishing_user_report | email.message_id | 24 hours | Same email reported multiple times |
| phishing_campaign | campaign.subject_pattern | 24 hours | Same campaign |
| endpoint_malware | host.name + malware.hash | 4 hours | Same malware on same host |
| ransomware_suspected | host.name + malware.family | 4 hours | Same ransomware on host |
| cloud_storage_public | resource.id + account.id | 24 hours | Same resource misconfigured |
| privilege_escalation | target_user.id + role_name | 24 hours | Same user granted same role |
| password_spray | source.ip | 1 hour | Same attacker IP |
| data_exfil_suspected | user.id | 1 hour | Same user exfiltrating |
| lost_device | device.id | 24 hours | Same device reported |

---

## Default Suppression Rules

### Rule 1: Suspicious Logins
```yaml
name: "Dedupe suspicious logins per user+IP (1 hour)"
alert_types: [suspicious_login]
time_window_minutes: 60
max_occurrences: 1
group_by_fields: ["user.id", "source.ip"]
escalate_after_count: 5  # Create incident after 5 attempts
```

**Behavior:**
- First suspicious login → Create incident
- Repeat within 1 hour → Suppress (update dedup count)
- After 5 occurrences → Escalate (create new incident)

### Rule 2: Endpoint Malware
```yaml
name: "Dedupe malware per host+hash (4 hours)"
alert_types: [endpoint_malware]
time_window_minutes: 240
max_occurrences: 1
group_by_fields: ["host.name", "malware.hash"]
escalate_if_severity: [critical]
```

**Behavior:**
- First malware detection → Create incident
- Same malware on same host within 4 hours → Suppress
- If severity becomes critical → Escalate

### Rule 3: Phishing Reports
```yaml
name: "Dedupe phishing reports by message ID"
alert_types: [phishing_user_report]
time_window_minutes: 1440  # 24 hours
max_occurrences: 1
group_by_fields: ["email.message_id"]
```

**Behavior:**
- First report of email → Create incident
- Same email reported again → Suppress (link to original incident)

### Rule 4: Cloud Misconfigurations
```yaml
name: "Dedupe cloud misconfig per resource (24 hours)"
alert_types: [cloud_storage_public]
time_window_minutes: 1440
max_occurrences: 1
group_by_fields: ["resource.id", "cloud.account_id"]
escalate_after_count: 3  # If not fixed after 3 detections
```

**Behavior:**
- First detection → Create incident
- Still public after 24 hours → Suppress
- After 3 occurrences (72 hours) → Escalate

---

## Database Schema

### detection_deduplication Table

Tracks unique detection patterns:

```sql
CREATE TABLE detection_deduplication (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    rule_id UUID NOT NULL,
    dedup_key TEXT NOT NULL,  -- SHA-256 hash
    dedup_fields JSONB NOT NULL,  -- {user_id: "...", source_ip: "..."}
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    incident_id UUID,  -- First incident created
    last_detection_event_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',  -- active, suppressed, resolved
    suppressed_until TIMESTAMPTZ,
    ...
);
```

### detection_suppression_rules Table

Configurable suppression policies:

```sql
CREATE TABLE detection_suppression_rules (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    alert_types TEXT[],  -- Which alerts to suppress
    time_window_minutes INTEGER NOT NULL,
    max_occurrences INTEGER NOT NULL,
    group_by_fields TEXT[],  -- Fields to group by
    escalate_after_count INTEGER,  -- Create incident after N
    escalate_if_severity TEXT[],  -- Escalate if severity changes
    ...
);
```

### detection_suppression_events Table

Audit log of suppressions:

```sql
CREATE TABLE detection_suppression_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    dedup_id UUID,
    detection_event_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    suppressed_at TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL,  -- 'duplicate', 'rate_limit', etc.
    ...
);
```

---

## Usage Examples

### Seed Default Suppression Rules

```bash
cd backend/services/soar_agent

python app/services/deduplication_service.py --tenant-id <UUID>
```

Output:
```
✓ Seeded 4 default suppression rules for tenant <UUID>
```

### View Deduplication Statistics

```sql
-- Count suppressed events in last 24 hours
SELECT 
    alert_type,
    COUNT(*) as suppressed_count
FROM detection_suppression_events
WHERE tenant_id = '<UUID>'
  AND suppressed_at > NOW() - INTERVAL '24 hours'
GROUP BY alert_type
ORDER BY suppressed_count DESC;
```

### View Active Dedup Records

```sql
-- See currently tracked patterns
SELECT 
    r.rule_key,
    d.dedup_fields,
    d.occurrence_count,
    d.first_seen,
    d.last_seen,
    d.incident_id
FROM detection_deduplication d
JOIN detection_rules r ON r.id = d.rule_id
WHERE d.tenant_id = '<UUID>'
  AND d.status = 'active'
ORDER BY d.last_seen DESC
LIMIT 20;
```

### Custom Suppression Rule

```sql
-- Create custom rule: suppress password sprays for 2 hours
INSERT INTO detection_suppression_rules (
    id, tenant_id, name, enabled, alert_types,
    time_window_minutes, max_occurrences, group_by_fields
)
VALUES (
    uuid_generate_v4(),
    '<tenant-uuid>',
    'Suppress password spray for 2 hours',
    true,
    ARRAY['password_spray'],
    120,  -- 2 hours
    1,
    ARRAY['source.ip']
);
```

---

## Suppression Reasons

| Reason | Description | Action |
|--------|-------------|--------|
| `duplicate` | Exact duplicate within time window | Suppress, update count |
| `rate_limit_max_N` | Exceeded max occurrences (N) | Suppress until window expires |
| `maintenance_window` | During scheduled maintenance | Suppress, log separately |
| `temporary_suppression` | Manual suppression by analyst | Suppress until end time |

---

## Escalation Policies

### Escalate After Count

If `escalate_after_count` is set, create new incident after N occurrences:

```
Occurrence 1: Create incident INC-001
Occurrence 2-4: Suppress (update dedup count)
Occurrence 5: Escalate → Create incident INC-002
```

Use case: Persistent attack attempts (password spray, failed logins)

### Escalate on Severity Change

If `escalate_if_severity` is set, create incident if severity increases:

```
First: severity=medium → Create INC-001
Repeat: severity=medium → Suppress
Repeat: severity=critical → Escalate → Create INC-002
```

Use case: Escalating threats (malware becomes ransomware)

---

## API Endpoints

### Check Deduplication Status

```
GET /api/v1/detection/deduplication/{dedup_key}

Returns:
{
  "dedup_key": "abc123...",
  "occurrence_count": 3,
  "first_seen": "2025-12-02T10:00:00Z",
  "last_seen": "2025-12-02T11:30:00Z",
  "incident_id": "550e8400-...",
  "status": "active"
}
```

### List Suppression Events

```
GET /api/v1/detection/suppression-events?hours=24

Returns:
{
  "events": [
    {
      "detection_event_id": "abc...",
      "alert_type": "suspicious_login",
      "suppressed_at": "2025-12-02T12:00:00Z",
      "reason": "duplicate"
    },
    ...
  ],
  "total": 47
}
```

### Create Custom Suppression Rule

```
POST /api/v1/detection/suppression-rules

Body:
{
  "name": "Custom suppression for test alerts",
  "alert_types": ["endpoint_malware"],
  "time_window_minutes": 180,
  "max_occurrences": 2,
  "group_by_fields": ["host.name"]
}
```

---

## Monitoring & Tuning

### Track Suppression Rate

```sql
-- Suppression rate by alert type
SELECT 
    alert_type,
    COUNT(*) as total_suppressions,
    COUNT(DISTINCT dedup_id) as unique_patterns
FROM detection_suppression_events
WHERE suppressed_at > NOW() - INTERVAL '7 days'
GROUP BY alert_type
ORDER BY total_suppressions DESC;
```

### Identify Noisy Rules

```sql
-- Rules with highest suppression rates
SELECT 
    r.rule_key,
    r.name,
    COUNT(DISTINCT d.dedup_key) as unique_patterns,
    SUM(d.occurrence_count) as total_occurrences,
    COUNT(DISTINCT d.incident_id) as incidents_created
FROM detection_deduplication d
JOIN detection_rules r ON r.id = d.rule_id
WHERE d.tenant_id = '<UUID>'
GROUP BY r.rule_key, r.name
ORDER BY total_occurrences DESC;
```

### Adjust Suppression Windows

```sql
-- Increase suppression window to 2 hours
UPDATE detection_suppression_rules
SET time_window_minutes = 120,
    updated_at = NOW()
WHERE alert_types @> ARRAY['suspicious_login']
  AND tenant_id = '<UUID>';
```

---

## Best Practices

### 1. Start Conservative

- **Short windows** (60 min) initially
- **Low max_occurrences** (1-2)
- Monitor suppression rates for 1 week
- Adjust based on data

### 2. Critical Alerts

- **Never suppress ransomware** (already configured)
- **Short windows for malware** (4 hours)
- **Escalate critical severity** immediately

### 3. False Positive Reduction

- **Longer windows for known noisy rules**
- **Higher max_occurrences** for benign patterns
- **Temporary suppression during maintenance**

### 4. Audit Trail

- **Always log suppressions** for compliance
- **Review weekly** for missed threats
- **Adjust rules quarterly** based on data

---

## Troubleshooting

### Too Many Suppressions

**Symptom:** High suppression rate (>50%)

**Solutions:**
1. Increase `escalate_after_count`
2. Reduce `time_window_minutes`
3. Review if rule is too sensitive

### Missing Incidents

**Symptom:** Expected incident not created

**Solutions:**
1. Check suppression logs
2. Verify dedup fields are correct
3. Review suppression rules

### Escalation Not Working

**Symptom:** Incidents not created after threshold

**Solutions:**
1. Verify `escalate_after_count` is set
2. Check occurrence_count in dedup record
3. Review suppression rule query

---

## Migration Path

### From No Deduplication

1. **Run migration 025:**
   ```bash
   psql -U sentinelgrid -d sentinelgrid_db -f backend/migrations/025_detection_deduplication.sql
   ```

2. **Seed default rules:**
   ```bash
   python backend/services/soar_agent/app/services/deduplication_service.py --tenant-id <UUID>
   ```

3. **Monitor for 1 week:**
   - Check suppression rates
   - Identify false positives
   - Tune thresholds

4. **Adjust rules** based on data

---

## Examples

### Example 1: Repeated Suspicious Login

```
10:00 AM: User alice attempts login from Russia (fails 5x, succeeds once)
  → Incident INC-001 created
  → Dedup record created: {user_id: alice, source_ip: 203.0.113.10}

10:15 AM: Same pattern repeats
  → Duplicate detected
  → occurrence_count updated to 2
  → Incident creation SUPPRESSED
  → Suppression logged

10:30 AM: Same pattern repeats (3rd time)
  → occurrence_count = 3
  → SUPPRESSED

11:00 AM: Same pattern repeats (5th time)
  → occurrence_count = 5
  → Escalate threshold reached
  → New incident INC-002 created
  → Alert: "Repeated suspicious login attempts (5x in 1 hour)"
```

### Example 2: Malware Redetection

```
9:00 AM: Malware hash ABC123 detected on host-01
  → Incident INC-003 created
  → Playbook executed: quarantine host
  → Dedup record: {host_name: host-01, malware_hash: ABC123}

9:30 AM: Same malware detected again (scan rerun)
  → Duplicate, suppressed (already handling it)

1:00 PM: (4 hours later, outside window)
  → Malware still present → New detection
  → New incident INC-004 created
  → Alert: "Malware persists after remediation attempt"
```

---

## Performance Considerations

### Index Optimization

The `detection_deduplication` table has partial index on active records:

```sql
CREATE INDEX idx_dedup_active 
ON detection_deduplication(tenant_id, dedup_key, last_seen DESC) 
WHERE status = 'active';
```

This optimizes the most common query (checking for active duplicates).

### Cleanup Policy

Old dedup records should be archived:

```sql
-- Archive dedup records older than 30 days
UPDATE detection_deduplication
SET status = 'archived'
WHERE last_seen < NOW() - INTERVAL '30 days'
  AND status = 'active';
```

Run this weekly via cron job.

---

## Compliance & Audit

### Suppression Audit Report

```sql
-- Generate suppression audit report
SELECT 
    DATE_TRUNC('day', suppressed_at) as date,
    alert_type,
    reason,
    COUNT(*) as count
FROM detection_suppression_events
WHERE tenant_id = '<UUID>'
  AND suppressed_at > NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', suppressed_at), alert_type, reason
ORDER BY date DESC, count DESC;
```

### Verify No Missed Threats

```sql
-- Check high occurrence counts that weren't escalated
SELECT 
    r.rule_key,
    d.dedup_fields,
    d.occurrence_count,
    d.first_seen,
    d.last_seen,
    s.escalate_after_count
FROM detection_deduplication d
JOIN detection_rules r ON r.id = d.rule_id
LEFT JOIN detection_suppression_rules s ON s.id = ANY(
    SELECT id FROM detection_suppression_rules 
    WHERE tenant_id = d.tenant_id 
    AND d.rule_id = detection_suppression_rules.rule_id
)
WHERE d.occurrence_count > 10
  AND d.status = 'active'
ORDER BY d.occurrence_count DESC;
```

---

## Summary

✅ **Alert Fatigue Reduced** - Duplicate events suppressed  
✅ **Visibility Maintained** - All events logged in audit trail  
✅ **Escalation Enabled** - Persistent issues still create incidents  
✅ **Configurable** - Per-tenant, per-alert-type rules  
✅ **Compliant** - Full audit trail for compliance

---

**Document Owner:** Security Engineering Team  
**Last Updated:** December 2, 2025

