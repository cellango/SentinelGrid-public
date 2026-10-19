# Native token-entry guard experiment

**Opt-in research fixture; never install or deploy its output.** The bounded P1
research approval in [ADR 0004](../../../../../docs/architecture/decisions/0004-issuer-core-storage-and-compatibility.md)
allows this experiment. It does not select a production fork or version. No
application, provider artifact, deployment or current authority changes follow.

## What was tested

The recipe verifies the exact `TokenEndpoint.java` bytes from upstream Keycloak
26.8.1 commit `24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b`. It copies that unit to a
separate temporary Maven project and inserts **one line at the beginning of
`processGrantRequest()`**, before CORS setup, form parsing, grant lookup and
`grant.preProcess`. The unmodified-source control compiles the same native unit.
No upstream source or binary is redistributed in this repository.

The denial-only probe uses a test-owner thread-local fixture. Missing, unknown,
closed or mismatched realm state denies. Only an explicit **unmanaged native
control** fixture continues to the native code. That seam is not durable enrollment,
an admission capability, a tenant authority or an HTTP configuration option.
Caller form/header hints cannot set it. Protected issuance is never allowed.

Both variants pass **34 tests each, zero skips**:

- Closed/unknown fixtures deny before any request read or grant lookup for ten
  native grant-factory IDs, an unknown extension ID and a missing grant type.
  The unmodified control reaches a deliberately throwing preprocessing sentinel
  for every non-null ID. This tests interception independently of grant dispatch;
  it does **not execute all ten native grant implementations**.
- Missing enrollment, another realm, nested fixture use, cleanup and another
  thread cannot acquire unmanaged control.
- Unmanaged controls execute the real endpoint, `AuthorizeClientUtil`,
  `AuthenticationProcessor`, `ClientAuthenticationFlow`, client-secret
  authenticator and native client-credentials grant. Wrong, missing, expired,
  disabled and unknown credentials/clients retain native denials. Valid synthetic
  authentication reaches a native service-account-disabled denial. An enabled
  client with no service account receives the native missing-account denial;
  no user is created. HTTP/context/model/storage/audit boundaries are doubles;
  native authentication results are not stubbed or statically mocked.

Eight additional preparation/SDK controls reject source or SDK drift, wrong mode,
symlinked native input, output inside the source tree, duplicate/extra dependency
coordinates and replacement of existing output. Earlier fixture setup errors were
corrected before these results; they are not enforcement witnesses. The native
unit and test-only protocol configuration use deprecated APIs, recorded as a
maintenance limitation rather than suppressed.

## Reproduce in an isolated directory

Use the exact separately reviewed source archive from the
[feasibility review](../../../../../docs/architecture/keycloak-issuer-feasibility.md),
an owned JDK 21 and Maven 3.9.11. Recorded execution used Temurin 21.0.12.1+1.
Use a new Maven home/repository, explicit credential-free settings mirroring only
Maven Central, and no injected Java/Maven options or annotation processors.
Review downloaded build plugins as executable inputs as well as SDK JARs.
The opt-in POM is separate from the provider's main POM and is not included in
its JAR, Compose or CI. The preparation script never invokes Maven or downloads.

From this directory, prepare two **new** output directories outside the source:

```sh
python3 prepare.py /path/to/keycloak-source /path/to/native-control native
python3 prepare.py /path/to/keycloak-source /path/to/guarded-control guarded
```

For each project, resolve its pinned dependencies with the owned Maven settings
and isolated cache, using `dependency:build-classpath` and an absolute
`-Dmdep.outputFile=/path/to/classpath.txt`. Before tests, verify the resolved JARs:

```sh
python3 verify_sdk.py /path/to/classpath.txt /path/to/isolated-maven-repository
```

Then use the same explicit Maven settings/cache with `test`, selecting
`-DentryGuard.guarded=false` in the native control and `true` in the guarded
control. Use offline mode once test plugins are reviewed and cached. The tests
assert that the compiled source overlay, rather than the dependency JAR's
endpoint, was loaded. Reflection-only Mockito fixtures and disabled dynamic agent
loading keep the final test JVM free of instrumentation agents. Keep raw reports
private. Delete the owned experiment directories afterward; never run `install`,
`deploy`, or place the output in a Keycloak providers directory.

[sdk-inputs.json](sdk-inputs.json) records the 206 resolved test-classpath JAR
coordinates, SHA-256 bytes and inherited POM license declarations. They include
Apache, BSD, MIT, Eclipse and GPL-with-classpath-exception declarations; this is
an isolated test dependency review, not a distribution license clearance or
security audit. Same-origin Central SHA-1 metadata was checked in addition to
local SHA-256 records; it is not independent signature verification. No JARs,
JDK, copied vendor source or built fixture artifacts are published here.

## Qualification boundary

This establishes a **method-body interception point only**. HTTP routing,
request filters, endpoint construction and earlier context/realm reads execute
outside it and remain unqualified. The thrown fixture exception has no qualified
HTTP error mapping. Browser authorization, broker, SAML and alternate native-auth
entry paths were not intercepted or executed. UMA and pre-authorized flow IDs
are intercepted at this method body, but their native special authentication
semantics and side effects remain unqualified. Successful issuance, real vaults,
signers, SQL, caches, providers, clusters and native transaction/HTTP durability
were not tested. No issuer process, database, actual workload credential/token
acquisition or data dispatch was started.

The [source audit](../core_audit/README.md) remains an incomplete callgraph.
All 22 writer families, including Client Admin API v2/shared client providers and
native realm SCIM resource writes, still require participation or enforceable
exclusion before protected reads/mutations. Runtime feature switches were not
qualified. This hook supplies no snapshot, generation, durable fence, conditional
grant, attempt ledger, recovery epoch or R3/R4 implementation. R2 implementation,
R3/R4, R5–R7, prior failed oracles, remaining R1 limits and IAM/service restoration
remain open. The next bounded research unit reviews front-door/constructor and
alternate-path admission gaps before further enforcement implementation.
