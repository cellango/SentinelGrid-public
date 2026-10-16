# Compliance Customer Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** Launch-ready customer reference  
**Updated:** 2026-04-28  
**Scope:** Compliance module behavior after Phase 8 gap closure.

## What Customers Can Do

Customers can use the Compliance module to:

- select supported compliance frameworks for their tenant;
- review framework-scoped control coverage, gaps, evidence freshness, and report readiness;
- collect IAM evidence into a durable evidence repository;
- review, accept, reject, retire, and recollect evidence;
- build evidence packages for audit periods;
- generate compliance reports with framework IDs, control IDs, evidence package IDs, and coverage snapshot metadata;
- schedule recurring compliance reports;
- review Compliance Agent recommendations before any write action is taken.

The module is evidence-backed where accepted, non-expired evidence exists. It is not an auditor attestation, legal opinion, or guarantee of compliance.

## Framework Support

| Framework | Shipped behavior | Customer-facing limitation |
| --- | --- | --- |
| SOC 2 | Readiness dashboard, selected-framework coverage, IAM evidence collection, evidence packages, report snapshots, supervised agent recommendations | Audit readiness depends on accepted, non-expired evidence and customer/auditor review. |
| HIPAA Security Rule | Tenant selection, control catalog, gap visibility, report scope inclusion, manual or IAM-linked evidence package inclusion | Legal compliance determination is not automated; unmapped controls remain not started or needs evidence. |
| PCI DSS | Tenant selection, control catalog, gap visibility, manual evidence package inclusion | CDE scoping and assessor-ready evidence are not fully automated. |
| NIST 800-171 | Tenant selection, control catalog, gap visibility, manual evidence package inclusion | CUI boundary validation is not automated. |
| ISO 27001 | Starter-pack positioning and trust workflow support | Full ISO 27001 catalog and statement of applicability are not shipped in this launch slice. |
| Customer Security Questionnaires | Questionnaire workflow support and reuse of report/evidence context | Questionnaire assist requires human review before sharing externally. |

## Admin Controls

Tenant admins can inspect and set the tenant-level Compliance launch controls through:

- `GET /api/v1/compliance/launch-readiness`
- `GET /api/v1/compliance/admin/settings`
- `PUT /api/v1/compliance/admin/settings`

Supported controls:

- `multi_framework_selection`
- `durable_evidence_repository`
- `compliance_agent_workflows`

Each tenant control is bounded by the platform environment flag:

- `COMPLIANCE_MULTI_FRAMEWORK_ENABLED`
- `COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED`
- `COMPLIANCE_AGENT_ENABLED`

If the platform flag is off, the tenant can see the control state but cannot make the feature effective until operators enable the platform flag.

## Demo Tenant

Use the dry-run first:

```bash
PYTHONPATH=backend/services/compliance_service:backend/libs \
  python backend/scripts/seed_compliance_launch_demo.py --tenant-slug demo
```

Apply after reviewing the output:

```bash
PYTHONPATH=backend/services/compliance_service:backend/libs \
  python backend/scripts/seed_compliance_launch_demo.py --tenant-slug demo --apply
```

The seed creates realistic selected frameworks, SOC 2 evidence package data, accepted IAM evidence items, a generated report record, a completed evidence collection task, and one proposed HIPAA missing-evidence recommendation.
