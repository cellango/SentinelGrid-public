# CIS Controls 1 & 2 Review (Codebase): Inventory + Onboarding for Employees, Devices, and Apps

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Scope: This is a **codebase-informed** review of SentinelGrid’s current onboarding/inventory capabilities against:
- **CIS Control 1 (v8)**: Inventory and Control of **Enterprise Assets** (devices/servers/network/cloud assets)
- **CIS Control 2 (v8)**: Inventory and Control of **Software Assets** (endpoint software + SaaS/integrated apps)

This is **not** a formal CIS compliance audit. The goal is to identify “day‑1 must‑haves” and gaps for:
- onboarding **employees**
- onboarding **devices**
- onboarding **apps**
…while enabling customers to meet CIS 1 & 2 in practice.

---

## Current Implementation (What Exists Today)

### Employees (Identity Inventory)
**UI**
- People directory + actions: `frontend/src/app/(dashboard)/dashboard/iam/people/page.tsx`
- Self‑service account management: `frontend/src/app/(dashboard)/dashboard/iam/my-account/page.tsx`

**Backend**
- User onboarding: invites + bulk CSV upload: `backend/agents/iam_agent/app/api/user_onboarding.py`
- Tenant-scoped IAM portal APIs (users, apps, entitlements): `backend/agents/iam_agent/app/api/iam_portal.py`
- Offboard/suspend actions exist in IAM portal flows (and UI bulk actions).

**Assessment vs CIS 1/2**
- CIS 1/2 are asset/software controls; identity inventory is primarily later controls (IAM), but it is still foundational for:
  - assigning **asset owners**
  - joining device/app inventory to a “human” record
  - safe offboarding (revoking access to enterprise and software assets)

**Key gap for frictionless onboarding**
- **Birthright rules** + **tenant setup** are planned but not implemented (see `docs/people_access_employee_lifecycle_plan.md`).

---

### Devices (Enterprise Asset Inventory)
**UI**
- Device inventory list + trust actions: `frontend/src/app/(dashboard)/dashboard/iam/devices/page.tsx`

**Backend**
- Device list API (queries `assets` table): `backend/agents/iam_agent/app/api/devices.py`
  - Uses `assets` table to return devices (asset_type, OS, IP, user_id, etc.)
  - Currently returns `trust_status="unknown"` for all devices and does not persist trust status.
  - `set_device_trust`, `revoke_device`, `get_device` are stubs/placeholders today.

**Data model**
- `assets` table contains many CMDB-ish fields and also “generic asset” columns:
  - `asset_type`, `asset_id`, `hostname`, `ip_address`, `operating_system`, `installed_software`, `user_id`, `owner`, `last_seen_at`, `metadata`, etc.
  - Verified in local DB via `\d+ assets` (Postgres) – it is a *single* shared assets table used across the platform.
  - Missing: a persisted `trust_status` column (currently implied/placeholder only).

**EDR telemetry**
- SentinelGuard server persists endpoint events to OpenSearch:
  - Ingest endpoint: `SentinelGuard/server/server.go`
  - OpenSearch persistence: `SentinelGuard/server/store_opensearch.go`
- SentinelGuard agent ships Wazuh-based events, but does **not** send a dedicated “device inventory / heartbeat” record today:
  - `SentinelGuard/agent/agent.go`

**Assessment vs CIS Control 1**
What we have:
- A **central inventory table** (`assets`) that can store the fields CIS wants.
- A **device inventory UI** and an API route that reads from the inventory table.
- EDR events flowing into OpenSearch (helps with passive discovery later).

What we do **not** have yet (important nuance):
- Cloud asset discovery via CloudQuery is **stubbed**: `backend/services/cmdb_service/app/services/cloud_query_integration.py` returns an empty list.
- A global “Enterprise Asset Inventory” UI page (servers/cloud/network/etc). Today we only have:
  - `/dashboard/iam/devices` (device subset)
  - ticket-level “CMDB” view (only when an incident/ticket is enriched)

Gaps blocking CIS 1 outcomes:
1) **No authoritative “device enrollment → inventory update” pipeline**
   - SentinelGuard events do not upsert/update `assets.last_seen_at` or device identity fields.
2) **No concept of authorized/unauthorized enterprise assets**
   - `trust_status` is not persisted; UI actions are mostly placeholders.
3) **No discovery posture**
   - We don’t measure coverage like “how many endpoints are reporting in the last 24h” vs “known inventory”.
4) **Data model fragmentation**
   - Endpoint “agent registration” exists in `customer_endpoint_agents` (onboarding tables), while device inventory UI reads from `assets` (tenant tables). This split prevents a clean, consistent CIS-1 experience unless unified.

---

### Apps (Software Asset Inventory)
**UI**
- App catalog + connect wizard: `frontend/src/app/(dashboard)/dashboard/iam/apps/catalog/page.tsx`
- App inventory list/detail: `/dashboard/iam/apps` and `/dashboard/iam/apps/[id]/edit`

**Backend**
- App catalog + connect endpoint(s): `backend/agents/iam_agent/app/api/app_catalog.py`
- App inventory endpoints: `backend/agents/iam_agent/app/api/apps.py`
- Assignments (roles to groups/users): `backend/agents/iam_agent/app/api/app_assignments.py`

**Data model**
- IAM Portal tables exist and are well-shaped for software access governance:
  - `apps`, `entitlements`, `access_profiles`, `user_entitlements`, `iam_audit_log` etc.
  - See `backend/migrations/015_iam_portal_schema.sql`.

**Assessment vs CIS Control 2**
What we have:
- A real **app inventory table** (`apps`) for tenant-scoped integrated apps.
- Role/entitlement model + assignments for access governance.

Gaps blocking CIS 2 outcomes:
1) **No “software inventory” for endpoints**
   - `assets.installed_software` exists but is not populated from an endpoint source today.
2) **No unauthorized/unsupported software detection**
   - No allowlist/denylist concept (authorized software catalog).
3) **No “app discovery” loop**
   - We can create apps via wizard, but do not automatically discover:
     - Keycloak clients created outside SentinelGrid UI
     - apps used by employees via login events (Keycloak audit logs / events)

---

## “Basic Functionality” Missing for CIS 1 & 2 (MVP Priority)

### Must-have to satisfy CIS 1 (Enterprise Asset Inventory)
1) **Persist device trust state**
   - Add `trust_status` (and optionally `trust_reason`, `trust_updated_at`) to the device inventory record.
   - Either:
     - extend `assets` table, or
     - create a `device_status` table keyed by `(tenant_id, asset_id/id)`.
2) **Implement real trust/revoke endpoints**
   - Replace placeholders in `backend/agents/iam_agent/app/api/devices.py` so the UI actions actually update persisted state.
3) **Make “last seen” real**
   - When device telemetry is received (SentinelGuard), update `assets.last_seen_at` and identify the device/host.
4) **Coverage/health view**
   - A simple “reporting in last 24h” counter and a “missing devices” list (inventory devices that have not checked in).

### Must-have to satisfy CIS 2 (Software Asset Inventory)
1) **Collect endpoint software inventory**
   - Define a minimal schema for installed software in `assets.installed_software`.
   - Add one ingestion path (agent-based preferred) that periodically reports:
     - package/software name
     - version
     - vendor/publisher (if available)
2) **Authorized software catalog**
   - Tenant-scoped allowlist/denylist policy that can drive:
     - “unauthorized software installed” detections
     - reporting views
3) **App discovery/import**
   - Add a “Discover/import from Keycloak” action so the app inventory can stay complete even if clients are created externally.

---

## Relationship Between Onboarding and CIS 1/2

To make onboarding “one click” and still meet CIS 1/2:
- **Employee onboarding** must apply birthrights so users land in correct teams and apps.
- **Device onboarding** must end with a real “managed device in inventory” record (with last seen).
- **App onboarding** must end with:
  - an inventory record,
  - entitlements defined,
  - assignments to teams/groups/users,
  - audit trail of who connected/activated the app.

If any of those are missing, customers will not experience “day‑1 inventory control”.

---

## Suggested Next Deliverables (Small, High-Impact)

1) **Tenant setup wizard (Day‑0)**
   - Configure Teams + Birthright Profiles + Birthright Rules + Invite defaults.
   - Documented in `docs/people_access_employee_lifecycle_plan.md` (needs implementation).
2) **Device inventory hardening**
   - Persist trust + real revoke + last_seen_at updates from SentinelGuard telemetry.
3) **Software inventory MVP**
   - Minimal installed software collection + “unsupported/unauthorized” reporting view.

---

## Notes / Technical Debt Observed

- There are multiple “CMDB/metadata service” modules that reference asset managers and models which appear stale or incomplete (e.g., missing `Asset` ORM model in `backend/libs/sg_core/models.py` while other services import it).
- The **actual** working device inventory path today is the IAM Agent querying the `assets` table via SQL (`backend/agents/iam_agent/app/api/devices.py`).

Recommendation: for CIS 1/2 work, treat the `assets` table as the source of truth and build a single, tenant-aware ingestion/update pathway for it (avoid splitting inventory into multiple competing services).
