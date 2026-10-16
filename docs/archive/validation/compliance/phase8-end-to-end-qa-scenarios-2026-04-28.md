# Phase 8 End-To-End Compliance QA Scenarios

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2026-04-28

## Purpose

Provide the launch validation path for the Compliance module from framework selection through evidence-backed reporting and supervised Compliance Agent approval.

## Automated QA Coverage

Run the executable backend scenarios:

```bash
cd backend/services/compliance_service
PYTHONPATH=.:../../libs pytest tests/test_phase8_end_to_end_qa.py
```

```bash
cd backend/services/reporting_service
PYTHONPATH=.:../../libs pytest tests/test_phase8_end_to_end_qa.py
```

These tests are intentionally service-local and use tenant-scoped dependency overrides rather than a live database. They prove API contracts, tenant context propagation, role-gated actions, report inputs, and recommendation state transitions.

## Scenario Map

| # | Scenario | Automated proof |
| --- | --- | --- |
| 1 | New tenant selects SOC 2 and HIPAA during onboarding | `compliance_service/tests/test_phase8_end_to_end_qa.py` asserts onboarding-sourced SOC 2 and HIPAA selections |
| 2 | Tenant changes selected frameworks in Compliance dashboard | same test replaces framework selections through `PUT /api/v1/compliance/framework-selections` |
| 3 | IAM evidence collection creates durable evidence and tasks | same test creates an IAM evidence collection task and evidence items |
| 4 | Evidence reviewer accepts and rejects evidence | same test accepts one evidence item and rejects a stale one |
| 5 | Coverage updates based on accepted evidence | same test asserts SOC 2 `CC6.1` moves to `operating` from accepted evidence only |
| 6 | User generates SOC 2 evidence report from an evidence package | `reporting_service/tests/test_phase8_end_to_end_qa.py` generates a SOC 2 PDF report with `evidence_package_ids` |
| 7 | User schedules monthly compliance status report | reporting test schedules the SOC 2 template monthly |
| 8 | Compliance Agent proposes missing evidence collection | compliance test triggers a high-priority HIPAA gap recommendation |
| 9 | User approves the agent recommendation | compliance test accepts the proposed recommendation |
| 10 | Cross-tenant access attempts fail | compliance test rejects cross-tenant framework/evidence requests; reporting test rejects a foreign tenant template schedule |

## Manual QA Notes

For a live tenant QA run, record:

- tenant ID and realm
- selected frameworks before and after dashboard changes
- evidence item IDs and review decisions
- evidence package ID and export ID
- generated report ID and compliance snapshot hash
- scheduled report job ID
- Compliance Agent recommendation ID and decision state
- failed cross-tenant request IDs

The report is audit-supporting only when it has a compliance snapshot hash and references concrete evidence package IDs. Legacy metadata-only reports from Phase 8.1 backfill must not be treated as evidence-backed reports.
