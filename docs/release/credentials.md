# Credential rotation applicability review

Task 2 is complete as of October 15, 2026. The owner confirmed that both published
defaults were used only in disposable local development. Together with the
local-only confirmation recorded in Task 1, this makes shared-environment rotation
not applicable for all four reviewed groups. This conclusion relies on owner
attestation and local source review; no live environment was inspected.

## Credential groups

| Group | Evidence | Rotation applicability |
| --- | --- | --- |
| Historical Keycloak client secret | Owner confirmed disposable local examples only in Task 1; exact value absent from candidate source | Shared-environment rotation not applicable |
| Vault root-token example | Owner confirmed disposable local examples only in Task 1; exact value absent from candidate source | Shared-environment rotation not applicable |
| Published Basic-auth administrator default | One reference at the Task 2 snapshot, inside a printed troubleshooting command; owner confirmed local development only | Shared-environment rotation not applicable |
| Published internal-service token default | 44 reference files at the Task 2 snapshot spanning docs, tests, guards, and runtime configuration; owner confirmed local development only | Shared-environment rotation not applicable |

The Basic-auth reference in `backend/scripts/test_realm_architecture.sh` is
printed with `echo`; the matching line does not execute an authentication request.
The script itself also contains destructive reset operations and was not run.

## Internal token usage

At the Task 2 snapshot, the 44 internal-token reference files comprised 11 documentation files, 19 test
files, three Compose files, four scripts/build targets, and seven runtime source
files. A test input or rejection guard is not evidence that a deployed service
accepts the default.

Task 3 subsequently omitted private business documents and sanitized example
metadata. The reference counts and hashes above describe the preserved Task 2
audit snapshot.

- Development Compose config supplies the fallback to 21 service definitions;
  minimal Compose supplies it to three; standalone AI Shield Compose supplies it
  to two. These are source configuration counts, not a live deployment inventory.
- The shared Python production validator rejects the known default when invoked.
  IAM and API Gateway settings invoke that validation in production. AI Shield's
  Python settings also reject the default in production.
- Offline observations show that the agent-runtime token functions and AI Shield
  Go gateway accept the known default when token configuration is absent, even
  with `ENVIRONMENT=production`. Configuring a different token makes the observed
  validation methods reject the old default.
- Go guardrail, provider-key, and telemetry clients and the certificate-enrollment
  helper contain outbound fallback behavior. The gateway `docker-run` target
  supplies the published token directly.

These experimental runtimes remain excluded from supported source-preview
execution. Before a runnable beta includes them, remove unsafe fallback acceptance
and verify explicit authentication configuration across receivers and senders.
The current review does not claim that those runtime defects are fixed.

## Local verification

| Check | Result |
| --- | --- |
| IAM configuration tests | 14 passed |
| API Gateway configuration tests | 7 passed |
| AI Shield production configuration test | 1 passed |
| Shared internal-auth helper tests | 4 passed |
| Agent-runtime token-function observations | 4 expected behaviors observed from original function bodies in isolation |
| AI Shield Go token-validation observations | 4 expected behaviors observed using the unchanged auth file in an isolated standard-library-only module |

The eight observations document both accepted and rejected requests; they are not
full-service security tests. No service was started, no live environment was
authenticated to, and no credential or Git history was changed.

## Closure decision

The owner answered the deployment-use question for both published defaults:
"No—both were local development only." Shared-environment rotation is therefore
recorded as not applicable, and Task 2 is closed. No remote revocation or rotation
is claimed. Historical copies and retained artifacts still need their separate
publication reviews.

If later evidence identifies shared use, reopen this decision, identify the
affected service/account and consumers, and review the coordinated replacement
plan. Verify authorized access succeeds and the old default fails after the
owner-authorized change. Revoke or rotate actual exposed credentials before
considering history removal, following
[GitHub's sensitive-data guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

The value-free reference audit, test results, offline observations, Compose
consumer inventory, and conditional rotation plan are local in ignored
`artifacts/private-release-review/task-2/`. Keep that evidence private. Continue
with the remaining tasks in
[the publication checklist](tasks.md).
