# Scan type field schema and demo seeding

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document pins the expected `summary` shape per `scan_type` and where we seed demo data so UI/API stay consistent.

## Common fields (all scan types)
- `findings` (int), `severity` (critical/high/medium/low/info)
- `remediation.summary|steps[]|validation[]`
- `nist_controls[]`, `mitre_techniques[]`
- `externally_exposed` (bool) when applicable
- `cves[]` when the engine reports CVE-aligned findings

## Per-type fields
- `cloud`: `failing_controls[]` (id, description, remediation), optional `soc2_criteria[]`
- `vuln` (container/endpoint vuln): `target_kind`, `cves[]` (id, cvss, description, fix)
- `host`: `target_kind`, `cves[]` (id, cvss, description, fix)
- `dast`: `target_url`, `evidence`, optional `target_kind`, optional `cves[]`
- `sast`: `file_path`, `line`, `rule_id`, `cwe`
- `secrets`: `file_path`, `line`, `secret_type`, optional `secret_sample`
- `iac`: `resource`, `control_id`, `desired_state`
- `git`: `repo`, `branch`, `last_commit`

## Seeding and migrations
- Demo seed script: `backend/services/scanner_orchestrator/app/seed_demo_scans.py` now writes `scan_type` explicitly and populates the per-type fields above for the demo tenant.
- Flyway migrations:
  - `V105__scan_type_and_public_view.sql` adds `scan_type` + normalization view.
  - `V107__seed_nist_mitre_scans.sql` and `V108__seed_host_scan_demo.sql` add NIST/MITRE and host samples.
  - `V109__enrich_other_scan_types.sql` enriches cloud/dast/sast/secrets/iac/git demos with richer fields.

These seeds ensure demo tenants surface realistic data for all scan types without exposing scanner engine names in the UI.
