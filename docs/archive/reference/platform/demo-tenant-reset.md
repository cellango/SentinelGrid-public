# Resetting the Demo Tenant (canonical catalog preserved)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Goal: remove demo-specific copies of detections/playbooks, recreate the demo tenant, and reseed so the demo only references the canonical system catalog (no duplicates).

## Prereqs
- Confirm the tenant IDs you want to use:
  - System (canonical) default: `9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0`
  - Demo default: `c6d82f67-36f1-4c7e-af66-d1333e45cde7`
  - Override via `SYSTEM_TENANT` / `DEMO_TENANT` env vars as needed.
- DB URL (default): `postgresql://sg:sg@localhost:5432/sg`

## Drop demo copies (safely)
Run in psql (replace `<DEMO_TENANT>`):
```sql
-- Remove demo-specific mappings/monitors and catalog rows
DELETE FROM detection_playbook_mappings WHERE tenant_id = '<DEMO_TENANT>';
DELETE FROM tenant_detection_monitors    WHERE tenant_id = '<DEMO_TENANT>';
DELETE FROM detection_rule_versions
  WHERE rule_id IN (SELECT id FROM detection_rules WHERE tenant_id = '<DEMO_TENANT>');
DELETE FROM detection_rules WHERE tenant_id = '<DEMO_TENANT>';
DELETE FROM playbooks       WHERE tenant_id = '<DEMO_TENANT>';

-- Optional: drop the demo tenant row itself
DELETE FROM tenants WHERE id = '<DEMO_TENANT>';
```

## Recreate the demo tenant row (if dropped)
```sql
INSERT INTO tenants (id, name, description, created_at, updated_at)
VALUES ('<DEMO_TENANT>', 'Demo', 'Demo tenant', NOW(), NOW());
```

## Reseed from the canonical catalog
```bash
export SYSTEM_TENANT=9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0
export DEMO_TENANT=c6d82f67-36f1-4c7e-af66-d1333e45cde7  # or your demo id
export DB_URL=postgresql://sg:sg@localhost:5432/sg

python backend/scripts/seed_catalog_detections_playbooks.py
```
The script now seeds detections/playbooks only into the system tenant as built-ins and creates demo mappings that point to those canonical rules/playbooks (no demo duplicates). Tenants can still clone to customize.

## Post-check
- `SELECT rule_key, tenant_id, is_builtin FROM detection_rules WHERE tenant_id = '<DEMO_TENANT>';` should return 0 rows (unless you deliberately cloned).
- `SELECT COUNT(*) FROM detection_playbook_mappings WHERE tenant_id = '<DEMO_TENANT>';` should be >0, pointing to system rule_ids/playbook_ids.
