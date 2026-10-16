-- Generated from catalog monitors; apply to system and demo tenants to replace match_all placeholders.
WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-NEW-ADMIN' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"terms": {"target_role.keyword": ["admin", "realm-admin", "super-admin", "PowerUser", "OrganizationAdmin"]}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-PRIV-GROUP-OFFHRS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"terms": {"group.name.keyword": ["admins", "security_admins"]}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'PRIV-GROUP-CHANGE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-MFA-DISABLED' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_mfa_root_issue',
        'playbook_id', 'MFA-BYPASS',
        'mitre_techniques', '["T1556"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-NEW-ACCESS-KEY-ADMIN' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-FAILED-LOGIN-BURST' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 5;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'PASSWORD-SPRAY',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-PASSWORD-SPRAY' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 10;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'PASSWORD-SPRAY',
        'mitre_techniques', '["T1110.003"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-IMPOSSIBLE-TRAVEL' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-NEW-COUNTRY-ASN' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-EXCESSIVE-STS-ASSUME' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 5;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-INACTIVE-USER-ACTIVITY' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-SERVICE-ACCT-NEW-LOC' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-MASS-LOCKOUTS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 3;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'PASSWORD-SPRAY',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-TOKEN-MISISSUE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_mfa_root_issue',
        'playbook_id', 'MFA-BYPASS',
        'mitre_techniques', '["T1550"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-REALM-CONFIG-CHANGE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'PRIV-GROUP-CHANGE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-ADMIN-NO-MFA' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_mfa_root_issue',
        'playbook_id', 'MFA-BYPASS',
        'mitre_techniques', '["T1556"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-AUTORUN-NEW' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1547"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-LOLBIN-SUSPICIOUS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1218"]'::jsonb,
        'mitre_tactics', '["TA0002"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-PRIV-ESC-ATTEMPT' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1068"]'::jsonb,
        'mitre_tactics', '["TA0004"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-NEW-RISKY-LISTENER' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"terms": {"destination.port": [22, 3389]}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1046", "T1105"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-MALWARE-DETECTED' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_malware_ransomware',
        'playbook_id', 'MALWARE-CONTAIN',
        'mitre_techniques', '["T1059", "T1204"]'::jsonb,
        'mitre_tactics', '["TA0002"]'::jsonb,
        'nist_controls', '["DE.CM", "RS.MI"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-RANSOMWARE-PATTERN' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'critical',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_malware_ransomware',
        'playbook_id', 'RANSOMWARE-IR',
        'mitre_techniques', '["T1486"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["DE.CM", "RS.MI"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-SCRIPT-TMP-WEBROOT' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1059"]'::jsonb,
        'mitre_tactics', '["TA0002"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-FIM-SYSTEM-PATH' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1565.001"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-NEW-LOCAL-USER' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1136.001"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-FAILED-SUDO-BURST' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 5;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0004"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-AGENT-OFFLINE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_monitoring_gap',
        'playbook_id', 'AGENT-OFFLINE',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-KERNEL-TAMPER' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1055", "T1562"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-UNAPPROVED-SOFTWARE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1195"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-SENSITIVE-FILE-ACCESS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1005"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-REMOTE-ACCESS-TOOLS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1219"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-INBOUND-SCAN' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'WAF-ATTACK',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-OUTBOUND-SCAN' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'EGRESS-ANOMALY',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-EXPLOIT-PUBLIC-SVC' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'WAF-ATTACK',
        'mitre_techniques', '["T1190"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-OUTBOUND-MALICIOUS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'C2/BEACON',
        'mitre_techniques', '["T1071"]'::jsonb,
        'mitre_tactics', '["TA0011"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-SUSPICIOUS-DNS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'C2/BEACON',
        'mitre_techniques', '["T1071.004"]'::jsonb,
        'mitre_tactics', '["TA0011"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-CLEARTEXT-PROD' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'EGRESS-ANOMALY',
        'mitre_techniques', '["T1040"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-NEW-EXTERNAL-EXPOSURE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'WAF-ATTACK',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-LARGE-EGRESS-NEW-IP' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'EGRESS-ANOMALY',
        'mitre_techniques', '["T1041"]'::jsonb,
        'mitre_tactics', '["TA0010"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-MULTI-AUTH-FAIL-SRCIP' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 10;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'PASSWORD-SPRAY',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-VPN-ANOMALY' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-C2-SIGNATURE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'C2/BEACON',
        'mitre_techniques', '["T1071"]'::jsonb,
        'mitre_tactics', '["TA0011"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-TOR-PROXY' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'C2/BEACON',
        'mitre_techniques', '["T1090"]'::jsonb,
        'mitre_tactics', '["TA0011"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-LATERAL-SMB-RDP' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_lateral_movement',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1021"]'::jsonb,
        'mitre_tactics', '["TA0008"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-TLS-CERT-ANOMALY' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'WAF-ATTACK',
        'mitre_techniques', '["T1553"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-SG-OPEN-CRITICAL' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"terms": {"destination.port": [22, 3389, 1433, 3306]}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_public_exposure',
        'playbook_id', 'SG-OPEN-CRITICAL',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["PR.AC", "PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-PUBLIC-STORAGE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"term": {"subtype": "s3_bucket_public"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_public_exposure',
        'playbook_id', 'CLOUD-PUBLIC-STORAGE',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.DS", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-STORAGE-PII-UNENCRYPTED' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_public_exposure',
        'playbook_id', 'CLOUD-PUBLIC-STORAGE',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.DS", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-EXCESSIVE-GET-LIST' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'EGRESS-ANOMALY',
        'mitre_techniques', '["T1041"]'::jsonb,
        'mitre_tactics', '["TA0010"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-SG-OPEN-SENSITIVE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_public_exposure',
        'playbook_id', 'SG-OPEN-CRITICAL',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["PR.AC", "PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-ROOT-USE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_mfa_root_issue',
        'playbook_id', 'ROOT-USE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-NEW-PRIV-ROLE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'PRIV-GROUP-CHANGE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-CHANGE-NO-TICKET' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-K8S-CLUSTER-ADMIN' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'k8s_misconfiguration',
        'playbook_id', 'K8S-PRIV-POD',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-K8S-PRIV-POD' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'k8s_misconfiguration',
        'playbook_id', 'K8S-PRIV-POD',
        'mitre_techniques', '["T1548"]'::jsonb,
        'mitre_tactics', '["TA0004"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-UNAPPROVED-REGISTRY' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'k8s_misconfiguration',
        'playbook_id', 'K8S-PRIV-POD',
        'mitre_techniques', '["T1195"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-NEW-EXTERNAL-PRINCIPAL' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-MASS-DELETE-STOP' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_logging_integrity',
        'playbook_id', 'RANSOMWARE-IR',
        'mitre_techniques', '["T1529"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["RS.MI"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-CLOUDTRAIL-DISABLED' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_logging_integrity',
        'playbook_id', 'LOGGING-DISABLED',
        'mitre_techniques', '["T1562"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-KMS-KEY-DISABLE-DELETE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_logging_integrity',
        'playbook_id', 'KMS-KEY-DISABLED',
        'mitre_techniques', '["T1485"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-NEW-REGION-ACTIVITY' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-PUBLIC-PROD' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_misconfiguration',
        'playbook_id', 'DB-PUBLIC-EXPOSED',
        'mitre_techniques', '["T1530"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-UNENCRYPTED-STORAGE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_misconfiguration',
        'playbook_id', 'DB-PUBLIC-EXPOSED',
        'mitre_techniques', '["T1530"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-BULK-SELECT-SENSITIVE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_data_exfil',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1005"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["DE.CM", "PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-SVC-ACCOUNT-ANOMALY' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_data_exfil',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-SCHEMA-CHANGE-NONDBA' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_misconfiguration',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1491"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-MASS-DELETE-UPDATE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_data_exfil',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1499"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["DE.CM", "RS.MI"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-FAILED-LOGINS-BURST' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 5;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_auth_anomaly',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-ACCOUNT-CREATED-PROD' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_auth_anomaly',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-AUDIT-LOG-OFF' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_misconfiguration',
        'playbook_id', 'DB-AUDIT-OFF',
        'mitre_techniques', '["T1562"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-NEW-HOST-ACCESS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_auth_anomaly',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-SECRET-FOUND' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_secret_exposure',
        'playbook_id', 'SECRET-EXPOSURE',
        'mitre_techniques', '["T1552.001"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-IAC-HIGH-RISK' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_iac_misconfiguration',
        'playbook_id', 'IAC-HIGH-RISK',
        'mitre_techniques', '["T1587"]'::jsonb,
        'mitre_tactics', '["TA0042"]'::jsonb,
        'nist_controls', '["PR.IP", "PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-HARD-CODED-KEYS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_secret_exposure',
        'playbook_id', 'SECRET-EXPOSURE',
        'mitre_techniques', '["T1552.001"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-PRIV-IAM-IAC' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_iac_misconfiguration',
        'playbook_id', 'IAC-HIGH-RISK',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CI-TOKEN-LEAK-LOGS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_secret_exposure',
        'playbook_id', 'SECRET-EXPOSURE',
        'mitre_techniques', '["T1552.001"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-K8S-MANIFEST-RISK' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_iac_misconfiguration',
        'playbook_id', 'IAC-HIGH-RISK',
        'mitre_techniques', '["T1609"]'::jsonb,
        'mitre_tactics', '["TA0042"]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-SAST-HIGH' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_app_vulnerability',
        'playbook_id', 'SAST-HIGH',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-SENSITIVE-FILE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_secret_exposure',
        'playbook_id', 'SECRET-EXPOSURE',
        'mitre_techniques', '["T1552.001"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-NO-BRANCH-PROTECTION' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '["T1609"]'::jsonb,
        'mitre_tactics', '["TA0042"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CI-BYPASS-CHECKS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '["T1553"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-PROMPT-INJECTION-DET' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_prompt_injection',
        'playbook_id', 'AI-PROMPT-INJECTION',
        'mitre_techniques', '["prompt_injection"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-DATA-LEAKAGE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_data_leak',
        'playbook_id', 'AI-DATA-LEAK',
        'mitre_techniques', '["data_leak"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.DS", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-POLICY-VIOLATION' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_usage_anomaly',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["policy_violation"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-TOOL-CALL-ANOMALY' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_tool_misuse',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["tool_anomaly"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-EXCESSIVE-TOKENS' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_usage_anomaly',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["usage_anomaly"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-NEW-APP-UNREGISTERED' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_usage_anomaly',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["unauthorized_app"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-ENDPOINT-NEW-REGION' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_usage_anomaly',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["geo_anomaly"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-JAILBREAK-BURST' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 3;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_prompt_injection',
        'playbook_id', 'AI-PROMPT-INJECTION',
        'mitre_techniques', '["prompt_injection"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-UNSAFE-TOOL-ACTION' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_tool_misuse',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["unsafe_tool"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-GATEWAY-CONFIG-CHANGE' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '["config_change"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.IP", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-LOGGING-DISABLED' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'LOGGING-DISABLED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-SIEM-PIPELINE-STALLED' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-30m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_gap',
        'playbook_id', 'LOGGING-DISABLED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-AGENT-OUTDATED' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1d"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_gap',
        'playbook_id', 'AGENT-OFFLINE',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-BACKUP-FAILURES' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1d"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_job_failure',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-CERT-EXPIRING' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1d"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-TIME-DRIFT' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-POLICY-DRIFT' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-NO-DETECTIONS-LONG' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_gap',
        'playbook_id', 'LOGGING-DISABLED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-TICKETING-WEBHOOK-FAIL' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_job_failure',
        'playbook_id', 'EXEC-NOTIFY',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["RS.CO"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-CONNECTOR-MISSING' AND tenant_id = '00000000-0000-0000-0000-000000000000'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-NEW-ADMIN' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"terms": {"target_role.keyword": ["admin", "realm-admin", "super-admin", "PowerUser", "OrganizationAdmin"]}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-PRIV-GROUP-OFFHRS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"terms": {"group.name.keyword": ["admins", "security_admins"]}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'PRIV-GROUP-CHANGE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-MFA-DISABLED' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_mfa_root_issue',
        'playbook_id', 'MFA-BYPASS',
        'mitre_techniques', '["T1556"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-NEW-ACCESS-KEY-ADMIN' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-FAILED-LOGIN-BURST' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 5;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'PASSWORD-SPRAY',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-PASSWORD-SPRAY' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 10;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'PASSWORD-SPRAY',
        'mitre_techniques', '["T1110.003"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-IMPOSSIBLE-TRAVEL' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-NEW-COUNTRY-ASN' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-EXCESSIVE-STS-ASSUME' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 5;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-INACTIVE-USER-ACTIVITY' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-SERVICE-ACCT-NEW-LOC' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-MASS-LOCKOUTS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 3;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'PASSWORD-SPRAY',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-TOKEN-MISISSUE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_mfa_root_issue',
        'playbook_id', 'MFA-BYPASS',
        'mitre_techniques', '["T1550"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-REALM-CONFIG-CHANGE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'PRIV-GROUP-CHANGE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'ID-ADMIN-NO-MFA' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_mfa_root_issue',
        'playbook_id', 'MFA-BYPASS',
        'mitre_techniques', '["T1556"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-AUTORUN-NEW' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1547"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-LOLBIN-SUSPICIOUS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1218"]'::jsonb,
        'mitre_tactics', '["TA0002"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-PRIV-ESC-ATTEMPT' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1068"]'::jsonb,
        'mitre_tactics', '["TA0004"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-NEW-RISKY-LISTENER' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"terms": {"destination.port": [22, 3389]}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1046", "T1105"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-MALWARE-DETECTED' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_malware_ransomware',
        'playbook_id', 'MALWARE-CONTAIN',
        'mitre_techniques', '["T1059", "T1204"]'::jsonb,
        'mitre_tactics', '["TA0002"]'::jsonb,
        'nist_controls', '["DE.CM", "RS.MI"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-RANSOMWARE-PATTERN' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'critical',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_malware_ransomware',
        'playbook_id', 'RANSOMWARE-IR',
        'mitre_techniques', '["T1486"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["DE.CM", "RS.MI"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-SCRIPT-TMP-WEBROOT' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1059"]'::jsonb,
        'mitre_tactics', '["TA0002"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-FIM-SYSTEM-PATH' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1565.001"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-NEW-LOCAL-USER' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1136.001"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-FAILED-SUDO-BURST' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 5;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0004"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-AGENT-OFFLINE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_monitoring_gap',
        'playbook_id', 'AGENT-OFFLINE',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-KERNEL-TAMPER' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1055", "T1562"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-UNAPPROVED-SOFTWARE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1195"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-SENSITIVE-FILE-ACCESS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1005"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'EP-REMOTE-ACCESS-TOOLS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'endpoint_suspicious_activity',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1219"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-INBOUND-SCAN' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'WAF-ATTACK',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-OUTBOUND-SCAN' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'EGRESS-ANOMALY',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-EXPLOIT-PUBLIC-SVC' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'WAF-ATTACK',
        'mitre_techniques', '["T1190"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-OUTBOUND-MALICIOUS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'C2/BEACON',
        'mitre_techniques', '["T1071"]'::jsonb,
        'mitre_tactics', '["TA0011"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-SUSPICIOUS-DNS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'C2/BEACON',
        'mitre_techniques', '["T1071.004"]'::jsonb,
        'mitre_tactics', '["TA0011"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-CLEARTEXT-PROD' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'EGRESS-ANOMALY',
        'mitre_techniques', '["T1040"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-NEW-EXTERNAL-EXPOSURE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'WAF-ATTACK',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-LARGE-EGRESS-NEW-IP' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'EGRESS-ANOMALY',
        'mitre_techniques', '["T1041"]'::jsonb,
        'mitre_tactics', '["TA0010"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-MULTI-AUTH-FAIL-SRCIP' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 10;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'PASSWORD-SPRAY',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-VPN-ANOMALY' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_auth_anomaly',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-C2-SIGNATURE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'C2/BEACON',
        'mitre_techniques', '["T1071"]'::jsonb,
        'mitre_tactics', '["TA0011"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-TOR-PROXY' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'C2/BEACON',
        'mitre_techniques', '["T1090"]'::jsonb,
        'mitre_tactics', '["TA0011"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-LATERAL-SMB-RDP' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_lateral_movement',
        'playbook_id', 'ENDPOINT-ISOLATE',
        'mitre_techniques', '["T1021"]'::jsonb,
        'mitre_tactics', '["TA0008"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-TLS-CERT-ANOMALY' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_recon_exploit',
        'playbook_id', 'WAF-ATTACK',
        'mitre_techniques', '["T1553"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'NW-SG-OPEN-CRITICAL' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"terms": {"destination.port": [22, 3389, 1433, 3306]}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_public_exposure',
        'playbook_id', 'SG-OPEN-CRITICAL',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["PR.AC", "PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-PUBLIC-STORAGE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}, {"term": {"subtype": "s3_bucket_public"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_public_exposure',
        'playbook_id', 'CLOUD-PUBLIC-STORAGE',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.DS", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-STORAGE-PII-UNENCRYPTED' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_public_exposure',
        'playbook_id', 'CLOUD-PUBLIC-STORAGE',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.DS", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-EXCESSIVE-GET-LIST' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'network_c2_egress',
        'playbook_id', 'EGRESS-ANOMALY',
        'mitre_techniques', '["T1041"]'::jsonb,
        'mitre_tactics', '["TA0010"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-SG-OPEN-SENSITIVE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_public_exposure',
        'playbook_id', 'SG-OPEN-CRITICAL',
        'mitre_techniques', '["T1046"]'::jsonb,
        'mitre_tactics', '["TA0007"]'::jsonb,
        'nist_controls', '["PR.AC", "PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-ROOT-USE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_mfa_root_issue',
        'playbook_id', 'ROOT-USE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-NEW-PRIV-ROLE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'PRIV-GROUP-CHANGE',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-CHANGE-NO-TICKET' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-K8S-CLUSTER-ADMIN' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'k8s_misconfiguration',
        'playbook_id', 'K8S-PRIV-POD',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-K8S-PRIV-POD' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'k8s_misconfiguration',
        'playbook_id', 'K8S-PRIV-POD',
        'mitre_techniques', '["T1548"]'::jsonb,
        'mitre_tactics', '["TA0004"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-UNAPPROVED-REGISTRY' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'k8s_misconfiguration',
        'playbook_id', 'K8S-PRIV-POD',
        'mitre_techniques', '["T1195"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-NEW-EXTERNAL-PRINCIPAL' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-MASS-DELETE-STOP' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_logging_integrity',
        'playbook_id', 'RANSOMWARE-IR',
        'mitre_techniques', '["T1529"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["RS.MI"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-CLOUDTRAIL-DISABLED' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_logging_integrity',
        'playbook_id', 'LOGGING-DISABLED',
        'mitre_techniques', '["T1562"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-KMS-KEY-DISABLE-DELETE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'cloud_logging_integrity',
        'playbook_id', 'KMS-KEY-DISABLED',
        'mitre_techniques', '["T1485"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CLD-NEW-REGION-ACTIVITY' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'identity_privilege_escalation',
        'playbook_id', 'ACCOUNT-COMPROMISE',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-PUBLIC-PROD' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_misconfiguration',
        'playbook_id', 'DB-PUBLIC-EXPOSED',
        'mitre_techniques', '["T1530"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-UNENCRYPTED-STORAGE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_misconfiguration',
        'playbook_id', 'DB-PUBLIC-EXPOSED',
        'mitre_techniques', '["T1530"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-BULK-SELECT-SENSITIVE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_data_exfil',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1005"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["DE.CM", "PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-SVC-ACCOUNT-ANOMALY' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_data_exfil',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-SCHEMA-CHANGE-NONDBA' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_misconfiguration',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1491"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-MASS-DELETE-UPDATE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_data_exfil',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1499"]'::jsonb,
        'mitre_tactics', '["TA0040"]'::jsonb,
        'nist_controls', '["DE.CM", "RS.MI"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-FAILED-LOGINS-BURST' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 5;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_auth_anomaly',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1110"]'::jsonb,
        'mitre_tactics', '["TA0006"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-ACCOUNT-CREATED-PROD' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_auth_anomaly',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-AUDIT-LOG-OFF' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_misconfiguration',
        'playbook_id', 'DB-AUDIT-OFF',
        'mitre_techniques', '["T1562"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'DB-NEW-HOST-ACCESS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'db_auth_anomaly',
        'playbook_id', 'DB-BULK-SELECT',
        'mitre_techniques', '["T1078"]'::jsonb,
        'mitre_tactics', '["TA0001"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-SECRET-FOUND' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_secret_exposure',
        'playbook_id', 'SECRET-EXPOSURE',
        'mitre_techniques', '["T1552.001"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-IAC-HIGH-RISK' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_iac_misconfiguration',
        'playbook_id', 'IAC-HIGH-RISK',
        'mitre_techniques', '["T1587"]'::jsonb,
        'mitre_tactics', '["TA0042"]'::jsonb,
        'nist_controls', '["PR.IP", "PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-HARD-CODED-KEYS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_secret_exposure',
        'playbook_id', 'SECRET-EXPOSURE',
        'mitre_techniques', '["T1552.001"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-PRIV-IAM-IAC' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_iac_misconfiguration',
        'playbook_id', 'IAC-HIGH-RISK',
        'mitre_techniques', '["T1098"]'::jsonb,
        'mitre_tactics', '["TA0003"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CI-TOKEN-LEAK-LOGS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_secret_exposure',
        'playbook_id', 'SECRET-EXPOSURE',
        'mitre_techniques', '["T1552.001"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-K8S-MANIFEST-RISK' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_iac_misconfiguration',
        'playbook_id', 'IAC-HIGH-RISK',
        'mitre_techniques', '["T1609"]'::jsonb,
        'mitre_tactics', '["TA0042"]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-SAST-HIGH' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_app_vulnerability',
        'playbook_id', 'SAST-HIGH',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-SENSITIVE-FILE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'git_secret_exposure',
        'playbook_id', 'SECRET-EXPOSURE',
        'mitre_techniques', '["T1552.001"]'::jsonb,
        'mitre_tactics', '["TA0009"]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'GIT-NO-BRANCH-PROTECTION' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '["T1609"]'::jsonb,
        'mitre_tactics', '["TA0042"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'CI-BYPASS-CHECKS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '["T1553"]'::jsonb,
        'mitre_tactics', '["TA0005"]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-PROMPT-INJECTION-DET' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_prompt_injection',
        'playbook_id', 'AI-PROMPT-INJECTION',
        'mitre_techniques', '["prompt_injection"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-DATA-LEAKAGE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-5m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_data_leak',
        'playbook_id', 'AI-DATA-LEAK',
        'mitre_techniques', '["data_leak"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.DS", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-POLICY-VIOLATION' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_usage_anomaly',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["policy_violation"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-TOOL-CALL-ANOMALY' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_tool_misuse',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["tool_anomaly"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-EXCESSIVE-TOKENS' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_usage_anomaly',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["usage_anomaly"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-NEW-APP-UNREGISTERED' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_usage_anomaly',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["unauthorized_app"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-ENDPOINT-NEW-REGION' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-15m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_usage_anomaly',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["geo_anomaly"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-JAILBREAK-BURST' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 3;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_prompt_injection',
        'playbook_id', 'AI-PROMPT-INJECTION',
        'mitre_techniques', '["prompt_injection"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-UNSAFE-TOOL-ACTION' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'ai_tool_misuse',
        'playbook_id', 'AI-POLICY-VIOLATION',
        'mitre_techniques', '["unsafe_tool"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.AC", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'AI-GATEWAY-CONFIG-CHANGE' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '["config_change"]'::jsonb,
        'mitre_tactics', '["custom"]'::jsonb,
        'nist_controls', '["PR.IP", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-LOGGING-DISABLED' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'high',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'LOGGING-DISABLED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-SIEM-PIPELINE-STALLED' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-30m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_gap',
        'playbook_id', 'LOGGING-DISABLED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-AGENT-OUTDATED' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1d"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_gap',
        'playbook_id', 'AGENT-OFFLINE',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-BACKUP-FAILURES' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1d"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_job_failure',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-CERT-EXPIRING' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1d"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.DS"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-TIME-DRIFT' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-POLICY-DRIFT' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP", "DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-NO-DETECTIONS-LONG' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'low',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_gap',
        'playbook_id', 'LOGGING-DISABLED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["DE.CM"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-TICKETING-WEBHOOK-FAIL' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-1h"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_job_failure',
        'playbook_id', 'EXEC-NOTIFY',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["RS.CO"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;

WITH rule_row AS (
    SELECT id FROM detection_rules
    WHERE rule_key = 'HG-CONNECTOR-MISSING' AND tenant_id = 'c6d82f67-36f1-4c7e-af66-d1333e45cde7'
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
)
SELECT
    rule_row.id,
    'v1',
    'sg-{tenant_id}-*',
    '{"size": 0, "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": "now-10m"}}}, {"term": {"sg.tenant_id": "{tenant_id}"}}]}}}',
    '{"script": {"source": "return ctx.results[0].hits.total.value >= 1;"}}',
    'medium',
    '{}'::jsonb,
    jsonb_build_object(
        'alert_type', 'monitoring_detection_integrity',
        'playbook_id', 'DRIFT-DETECTED',
        'mitre_techniques', '[]'::jsonb,
        'mitre_tactics', '[]'::jsonb,
        'nist_controls', '["PR.IP"]'::jsonb
    )
FROM rule_row
ON CONFLICT (rule_id, version) DO UPDATE
SET index_pattern = EXCLUDED.index_pattern,
    query = EXCLUDED.query,
    trigger_condition = EXCLUDED.trigger_condition,
    severity = EXCLUDED.severity,
    metadata = EXCLUDED.metadata;
