# MCP case proposal records

Status: partial implementation, opt-in authenticated HTTP profile. This connects the real MCP SDK to the existing [action proposal API](action-authority.md). It grants no provider execution, approval or case closure. Required legacy tools remain unavailable pending their domain qualifications.

## Two explicit record operations

| Wire name | Logical operation | Receiving API permission | Behavior |
| --- | --- | --- | --- |
| `case_propose_action` | `case.propose_action` | `propose` on the exact case | Record an immutable proposal and approval request. |
| `case_get_action_proposal` | `case.get_action_proposal` | `read` on the exact case | Inspect the proposal and current approval state. |

Mapping version is `CASE_RECORD_MAPPING_VERSION=1`. These names are distinct from the retained legacy `lock_account`/`identity.lock_account` execution capability. The factory's default profile and stdio surface retain their previous denial behavior. An owned `CaseRecordPolicy` passed to `create_verified_http_app` can add both record operations, or inspection only. The factory is still not installed by a deployment entrypoint.

Proposal arguments are exactly `case_id`, `request_key` (canonical non-nil UUID) and `proposal`. The nested proposal uses the [shared versioned contract](../../backend/libs/sg_core/action_contracts.py); currently the receiver admits only the `identity.lock_account` / `source-preview-v1` intent shape. Read arguments are exactly `case_id` and `proposal_id`. Extra tenant, actor, credential, destination or approval arguments are rejected. No MCP approval, reservation, execution, receipt or verification tool is exposed.

## Identity and deterministic authority

Every MCP POST authenticates a fresh bearer through the owned IAM contract and user/client binding. Cookies, identity headers, workload identities and unbound clients cannot select a caller. The SDK carries that exact request into the handler; the handler checks its private transport context against the verified credential again. Constructing a caller object or setting public request state does not grant access. Concurrent requests retain their own verified subject.

The operation profile allows an attempt to submit or read records. It does not grant case access. The bridge forwards the selected bearer and its verified tenant to one owned receiver origin. The receiver independently authenticates that bearer and checks current case grants, tenant RLS, case/plan/policy revision and expiry. The same audience and user-binding configuration must legitimately accept that credential at both boundaries; the bridge does not exchange or manufacture a token. It never uses a shared service credential or caller-supplied trusted identity.

Human approval remains at the receiving API with a separate authorized approver. A model cannot supply an approval flag, approve through these tools or execute an approved proposal. Replies always contain boolean `execution_available=false`, including an `approved` record. Submission metadata includes the verified `tenant_id` and exact `case_id`. Inspection also checks document IDs/revision and the RFC8785 proposal hash before returning content. Unexpected status, true/ambiguous execution flags, extra fields or foreign bindings fail closed.

## Transport and retries

The owned destination must be an HTTP origin without credentials, query, fragment or path; it must use HTTPS outside development/test. Model arguments cannot choose the origin or route. The client verifies TLS, supports an owned CA bundle, ignores proxy environment variables, follows no redirects and keeps no credential/cookie session. It uses a bounded total deadline and response size. The opt-in profile rejects duplicate JSON fields before SDK parsing and limits actual request bytes to 64 KiB; proposal canonicalization retains its 32 KiB bound. Existing peer and verified-identity request budgets apply. Production TLS/HA/capacity and model/provider spending controls remain separate qualification gates.

A timeout or lost response can occur after the receiving transaction commits. Retry the **same `request_key`, verified proposer and exact intent**. The receiver returns the existing proposal; changed content or proposer with that key conflicts. The bridge makes no automatic retry and never invents success on an uncertain response. Receiver failure bodies, credentials and configuration details are not echoed in tool errors. Identity expiry while waiting prevents release of the record response.

## Validation and limits

`make preview-mcp` exercises the real SDK HTTP protocol, signed user identities, operation profiles, legacy denial, argument/response binding, malformed/duplicate JSON, hash checks, timeouts and expiry using an owned HTTP receiver fixture. The separate `make preview-action-db` gate also runs actual MCP SDK → in-process ASGI receiving API → native Flyway/PostgreSQL tests, with no authentication, case-permission or storage handler replacement. Only IAM HTTP is a synthetic RSA-verifying fixture. Those checks include current grant denial, separate API approval, cross-case access, atomic storage failure, concurrent caller isolation, response loss after commit and an immediate PostgreSQL crash/restart. Missing native tools fail that separate gate.

This is bounded source and isolated-storage qualification. The ASGI test link is not a TCP/TLS deployment test. It does not restore any of the 26 required legacy provider tools, adopt an existing database, qualify the native issuer, enable Temporal scheduling or prove a real provider effect. Follow the root release scope and the remaining shared-platform acceptance gates.
