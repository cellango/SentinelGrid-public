# Action proposal and approval records

Status: partial implementation for source review. This is the PostgreSQL application-record part of `case_runtime`, the facade selected by [ADR0001](../architecture/decisions/0001-case-runtime.md). It does not start Temporal, dispatch providers, issue workload credentials or claim verified effects.

## Interfaces and identity

The gateway mounts exactly these routes and forwards the selected bearer, verified tenant and `Idempotency-Key` to its owned `CASE_RUNTIME_URL`. Direct calls require a bearer credential. Cookies and conflicting actor, tenant, realm, role or internal-token hints are rejected by the receiver. An administrator role does not grant case access. User/client classification uses the existing owned IAM verification contract; live issuer qualification is a separate requirement.

| Method | Route | Required case permission |
| --- | --- | --- |
| POST | `/api/v1/cases/{case_id}/action-proposals` | `propose` |
| GET | `/api/v1/cases/{case_id}/action-proposals/{proposal_id}` | `read` |
| POST | `/api/v1/cases/{case_id}/action-proposals/{proposal_id}/approvals` | `approve` |

Proposal creation requires one canonical non-nil UUID `Idempotency-Key`. A repeat with identical request bytes after canonicalization and the same verified proposer returns the existing record. Different content or proposer with that key returns HTTP 409. Case locking serializes concurrent submissions. Replays report current approval/expiry/revision state. Proposal creation, policy/approval request and outbox insertion commit together. Storage failure returns HTTP 503; there is no memory fallback.

Only the typed `identity.lock_account` / `source-preview-v1` proposal shape is currently admitted: one `identity.user` UUID target and a `reason` parameter of 1–2048 characters. This records an intent; it does not establish target ownership, enable that provider or restore another tool. All other required capabilities remain unavailable pending their typed domain contracts. Request bodies cannot supply tenant, actor, case/plan revision, policy version or an approval override.

## Exact proposal bytes and approval

The shared `sg_core/action_contracts.py` (re-exported by `app/authority/contracts.py`) defines schema `sentinelgrid-action-proposal-v1`. The immutable hashed object contains `schema`, `tenant_id`, `case_id`, `case_revision`, `plan_revision`, `policy_version`, `action_id`, `proposal_id`, `proposal_revision`, `proposed_by`, `tool_id`, `tool_version`, sorted `targets`, `parameters`, `expected_effect`, `risk`, `preconditions`, `compensation`, `verification` and `expires_at` (UTC epoch seconds). Target order is kind/resource UUID. RFC8785 UTF-8 bytes are SHA-256 hashed. The reviewed `rfc8785` package implements primitive number serialization and UTF-16 property order; duplicate fields, non-finite/unsafe numbers, invalid Unicode, excessive depth/collections and oversized canonical payloads are rejected. The [fixed vectors](../../backend/services/case_runtime/tests/canonical-vectors.json) include independent JavaScript byte/hash checks.

Approval requires the exact immutable hash and a separate currently authorized approver. Decisions append; they never rewrite proposal bytes or an older decision. Repeating the latest identical decision by the same approver returns its original ID. A rejection or revocation requires a new proposal. A reserved action cannot be relabeled cancelled by revoking approval. A new case/plan/policy revision invalidates the old proposal. Proposal and approval expire no later than the current grant; case permissions and approver authority are checked again for reservation. Approval is distinct from execution and verification.

The internal reservation method has no HTTP/MCP/worker execution route. It locks target fences in deterministic order, records a stable tenant/action effect key and allows one reservation per action. Any previous reservation for the resource blocks another action until authoritative reconciliation is implemented, even after lease expiry. It cannot dispatch, retry an uncertain effect, issue a token or manufacture a receipt. No release/recovery dispatcher is qualified.

## Storage and deployment limits

[Action storage profile](../../publication/action-authority-profile.json) pins the paired SQLAlchemy models and canonical V018 migration. V018 creates only the `case_runtime` schema with composite tenant/record/hash relationships, forced tenant RLS, append-only evidence and an outbox. It creates no roles, adopts no existing rows and changes no older migration. Runtime code never creates tables or runs migrations. Do not add this new schema's migration to the separate IAM-only history. The default native fixture is V018-only. The [shared database gate](application-database.md) separately qualifies the unchanged V001–V018 lineage and runs the27action/MCP tests in that full catalog; existing data adoption and production privileges remain open.

The authority is disabled by default (`ACTION_AUTHORITY_ENABLED=false`) and opens no database. An explicitly enabled instance requires an owned `postgresql+psycopg2` URL and a successfully migrated V018 history. Every transaction enforces the [dedicated database-role boundary](action-database-role.md), including unsafe role memberships, ownership, table/column grants, history writes and required RLS flags. It rejects superuser/BYPASSRLS application roles. Provision a separate migrator; runtime needs schema USAGE, history SELECT, tenant-filtered SELECT, INSERT only for proposal/approval/policy/claim/fence/attempt/outbox records and UPDATE(id) on cases/access grants solely for row locking, plus UPDATE(generation) on resource fences. It must not have CREATE, ownership, role management, TRUNCATE, INSERT on cases/grants, or UPDATE on authority-bearing case/grant columns. Case ownership, grant provisioning/revocation and their production rollout still need infrastructure qualification. The synthetic test grants are an isolated lab profile, not a deployment.

The receiver uses bounded body/header/concurrency admission and an owned `ACTION_RATE_POLICY`. Outside development/test it requires fail-closed budgets over TLS Redis and database TLS `verify-full`. Run Uvicorn with `--no-proxy-headers`. No production TLS/Redis failover/capacity, cost accounting, backup/recovery, retention, Temporal scheduling, data adoption or independent provider verification is claimed. `/ready` deliberately returns HTTP 503. Legacy action-service execution and direct helper bypasses return503, including `requires_approval=false`; its nine existing action types remain restoration requirements.

## Qualification

Ordinary source tests exercise real RSA-signed users against the owned IAM HTTP contract without overriding identity dependencies, strict JSON/canonicalization, forged identity/approval fields, exact gateway routing and legacy bypass containment. Run the separate native storage gate with reviewed PostgreSQL server tools and Flyway:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/libs:backend/services/case_runtime \
SG_TEST_PG_BINDIR=/path/to/reviewed/postgresql/bin \
SG_TEST_FLYWAY=/path/to/reviewed/flyway \
.venv/bin/python -m pytest -c backend/services/case_runtime/tests/pytest.ini \
-p no:cacheprovider backend/services/case_runtime/tests/test_action_database.py
```

The test creates its own synthetic loopback/SCRAM cluster and cleans it up. Missing tools fail the separate gate. Committed approvals and idempotency records are also checked after an actual immediate PostgreSQL crash/restart. It never uses `DATABASE_URL`, an existing cluster, SQLite, `create_all`, automatic baselining or repair. Provider, issuer, MCP execution and full end-to-end acceptance remain separate open gates.

## MCP record entrypoint

An [opt-in MCP record profile](mcp-case-records.md) submits and inspects proposals through these same API/grant/storage checks. Submission and inspection metadata now includes `tenant_id` and `case_id`. Proposal/hash bytes are unchanged. These tools cannot approve or execute an action.

## Case provisioning prerequisites

Cases and case grants already exist in V018, but no production provisioning
interface is admitted. The action application's INSERT/UPDATE restrictions are
intentional and must not be expanded merely to seed a workflow. An administrator
claim, tenant parameter or test-fixture owner does not supply case-creation or
grant-management authority. Before adding a writer, specify and qualify its
verified caller lifecycle, server-owned permission/source mapping, separation
from action execution, bounded grant expiry/revocation, atomic audit and outbox
records, and operational credential custody. Issuer qualification remains
separate; ordinary caller proof must not be confused with unqualified conditional
acquisition. No new writer is introduced by storage prerequisite tests.

The native action suite additionally checks all-or-nothing synthetic case/grant
provisioning on a uniqueness failure, composite tenant/case grant rejection,
application denial of grant creation/extension/deletion, and persisted grant
revocation across an actual PostgreSQL immediate crash/restart. Fixture writes
use the disposable lab owner; they do not demonstrate a least-privilege
production provisioner. Existing rows, V001-V018, application privileges and
default-disabled behavior remain unchanged.

The separate [V019 provenance extension](case-provenance-storage.md) adds paired
evidence-reference/link and immutable run-manifest/link storage with its own native
install/upgrade/recovery tests. It grants no application access and adds no writer.
Full provenance producer semantics, authorized provisioning, workflow storage,
runtime execution and end-to-end qualification remain incomplete.
