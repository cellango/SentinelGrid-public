# Detection/Playbook Tenant Model

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Goal: one canonical catalog of detections and playbooks; tenants consume the shared catalog and may clone to customize. No per-tenant duplication of the base set (including demo).

## Canonical catalog
- Stored under the **system tenant** (`is_builtin=true`).
- `detection_rules.rule_key` is unique per tenant; system tenant holds the authoritative row and versions.
- `detection_rule_versions` are attached to the canonical rule id.
- Playbooks follow the same pattern (`is_builtin=true` under system tenant).

## Tenant consumption
- API `list_rules` returns: tenant’s own non-builtin rules **plus** system-tenant built-ins. Same for playbooks via mappings.
- `tenant_detection_monitors` and `detection_playbook_mappings` are per-tenant, pointing at the canonical rule/playbook ids (unless the tenant cloned).
- Tenants can clone a built-in rule/playbook to their own tenant; clones are `is_builtin=false`, editable, and do not affect the canonical version.

## Seeding policy
- Seed catalog detections/playbooks **only** into the system tenant as built-ins.
- For demo/other tenants, seed only the mappings to the canonical rules/playbooks; do not duplicate the catalog rows.
- Environment overrides (`SYSTEM_TENANT`, `DEMO_TENANT`) let you target different ids when seeding.

## Current enforcement in code
- `list_rules` merges system built-ins + tenant-local rules; `clone_rule` creates tenant-scoped copies.
- `seed_catalog_detections_playbooks.py` updated to map demo → system rules instead of duplicating them.
- Validation/preview paths now reject match_all to avoid empty monitors.

## Cleanup guidance (if duplicates exist)
- Identify duplicates: `SELECT rule_key, tenant_id FROM detection_rules WHERE is_builtin=false AND tenant_id = <demo>;`
- For each duplicate, update `tenant_detection_monitors` and `detection_playbook_mappings` to point to the system rule id, then delete the duplicate `detection_rules` row (CASCADE will remove its versions).

This ensures one source of truth for the 110 detections/playbooks, with tenant-level overrides only when explicitly cloned.
