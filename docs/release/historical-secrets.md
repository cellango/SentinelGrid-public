# Historical secret match review

Task 1 is complete as of October 15, 2026. All **137 scanner rows** have a
supported classification. They represent **22 distinct values**, not 137 separate
credentials. The scan still reports those historical occurrences; classification
does not remove them or clear the repository for publication.

## Findings

| Classification | Scanner rows | Disposition |
| --- | --- | --- |
| Non-secret identifiers | 27 | Database address fragments, a detection rule ID, and realm resource IDs; no credential rotation indicated |
| Synthetic examples and placeholders | 37 | Truncated tokens, fixed scanner inputs, stub responses, instructional placeholders, and negative tests |
| Published default credentials | 60 | Two known default values; owner confirmed local development only in Task 2; shared-environment rotation not applicable |
| Owner-confirmed disposable local values | 13 | Two values; the owner confirmed both were disposable local examples only |
| Unresolved classifications | 0 | No finding remains unclassified |

The local-only values were the historical Keycloak client secret and the Vault
root-token example. The owner's confirmation resolves their environment scope;
no live authentication or revocation test was performed. Neither exact value
remains in the candidate source files.

The default-credential references include documentation, test inputs, rejection
guards, and configuration. A textual reference does not establish that an active
deployment accepts that value. The [Task 2 review](credentials.md)
distinguishes those cases and records the owner's local-only confirmation.

## Verification and scope

- Verified every scanner row against its reported historical source-line range.
- Traced all 60 rows inside the old scanner report to the embedded original
  finding and verified the value occurs in that original source. Those rows were
  classified by their underlying content, not dismissed as report duplicates.
- Inventoried 41 locally available Git refs and 359 reachable commits. The finding
  commits are reachable from 39 refs; the private ledger records the exact names
  and tips. This inventory does not establish the scope of remote-only refs.
- Searched 6,471 historical blobs for additional occurrences of the two local-only
  values. The Keycloak value also appeared in historical development/minimal
  Compose configuration. That is consistent with the owner's local-use account.
- Preserved both rows sharing one scanner fingerprint: the report has 137 rows
  and 136 distinct fingerprints. They are traceable individually by input row ID.
- Kept values, source excerpts, and unredacted scanner output out of this summary
  and the candidate source. No scanner exceptions or Git history were changed.

This review classifies the findings from the available history scan. It is not a
clearance of every possible secret, externally retained artifact, or remote ref.

## Private evidence and next task

The value-free ledger, input reports, ref inventory, occurrence evidence, and
reproduction script are local under ignored `artifacts/private-release-review/task-1/`.
The raw triage report contains credential material and must remain private.

Task 2 is also complete: the owner confirmed that both known defaults were used
only in disposable local development. Shared-environment rotation is not
applicable for the reviewed groups; no credentials were changed.
The [Task 3 private-data review](private-data.md) is also complete.
Historical-content disposition still belongs to the later publication-history
tasks. The [Task 4 provenance review](provenance.md) also records
excluded historical installers. Continue with the
[publication checklist](tasks.md).
