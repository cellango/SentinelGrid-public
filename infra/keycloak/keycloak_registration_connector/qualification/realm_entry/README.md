# Early realm-denial experiment

**Isolated denial-only research; never install or deploy its output.** The
[admission design](../../../../../docs/architecture/keycloak-native-admission.md)
and [ADR 0004](../../../../../docs/architecture/decisions/0004-issuer-core-storage-and-compatibility.md)
retain NO-GO for full admission, cleanup and R2 implementation/R3/R4.
This unit supplies a native method-hook result and a concrete negative lifecycle
result, not a production issuer change.

## Native comparison and result

The preparation recipe verifies five native source units from Keycloak 26.8.1
commit `24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b`, then compiles them into a new
isolated project. Only guarded `RealmsResource` differs: one first statement in
its static `resolveRealmAndUpdateSession` method, before `new RealmManager`.
Native RealmManager, DefaultKeycloakSession and DefaultKeycloakTransactionManager
execute from the exact matching reviewed SDK. Their source bytes are also checked
against the archive. No vendor source/JAR/JDK or built output is distributed here.

Both variants pass **130 test cases each, zero skips**:

- 96 realm/lifecycle cases per variant, including 65 route/state combinations.
  Thirteen native locator invocation variants cover OIDC/SAML/unknown protocol,
  login, broker, registration, client management, account, public realm, redirect,
  authorization, extension and discovery paths using the shared resolver.
  Guarded closed/unknown/ambiguous/lookup-error/incarnation-mismatch fixtures deny
  before realm lookup, context binding, trace/MDC or event/provider construction.
  The unmodified control reaches a deliberately throwing realm-provider lookup
  through the real native RealmManager. Explicit unmanaged fixtures preserve that
  behavior and the native missing-realm 404. These are locator method invocations,
  not HTTP routes or framework coverage. Fault-state names are test selectors,
  not a real primary-store lookup or incarnation proof.
- 34 unchanged native-authentication controls per variant are reused from the
  [token-entry lab](../entry_guard/README.md), with the native token endpoint
  unmodified. They execute real native authentication and client-credentials
  denial, including missing-account non-creation. No auth result is substituted
  and no token is issued or acquired.

Six preparation controls reject source/shared-control drift, symlinked source,
unknown mode, output inside the source tree and replacement of existing output.
`native-sources.json` and `shared-controls.json` pin the copied inputs. The
native overlay classes are checked as loaded from the temporary compiled source,
not silently replaced by the SDK JAR. Test-owner thread-local frames can only
select unmanaged native controls; caller hints, absent state, mismatched session/
hint, nested fixture installation, later reuse or another thread cannot obtain
that fixture. This is **not durable enrollment or caller authority**.

## Minimal failure path and failed cleanup gate

`MinimalDenialMapper` is called directly in the fixture. It is **not registered
in a real HTTP runtime**. Its fixed 503 JSON/no-store response reads no realm,
request, context, theme, locale or identity provider. Native transaction/session
code performs rollback-only/close in the ordinary tested path; the native close
filter accepts an already-closed session for an ordinary response entity. Marker
reuse and wrong-thread/foreign-session handling cannot close unrelated sessions.

The negative controls are part of the result:

1. Native generic HTML error handling attempts a realm lookup after denial,
   including the native admin-realm fallback when the path does not match. The
   throwing model sentinel produces a generic 500. This demonstrates why falling
   through that handler is unsuitable for the proposed pre-read contract; it
   does not establish a stock vulnerability or a tested HTTP mapper order.
2. An ordinary **unmarked native close commits** the synthetic control transaction.
   The fixture therefore refuses native default-close if an active transaction
   cannot be marked and verified rollback-only. Manager/marker/lifecycle/close
   faults keep the response unavailable and record an observed fault. Some fault
   paths leave the session open: complete resource cleanup is **not proved**.
3. A synthetic transaction participant throwing during native rollback leaves its
   state unfinished while the native transaction manager returns and the session
   reports closed. The mapper sees no propagated fault. This is reproduced with
   the real native manager/session and an in-memory throwing participant, **not a
   PostgreSQL/JDBC durability test**. `cleanupFaultObserved() == false`, session
   close and zero recorded commit calls cannot prove successful rollback.

The first test iteration expected that participant failure to propagate and
failed; the witness is retained. Final tests explicitly preserve this negative
result. Passing assertions describe the observation; **the rollback-failure
propagation and complete-cleanup gates remain failed**. No native rollback fix is
supplied here. Propagation/recovery behavior needs the next bounded lifecycle
experiment before further admission or storage qualification.

## Reproduce only in owned temporary projects

Use the exact separately reviewed archive from the
[feasibility review](../../../../../docs/architecture/keycloak-issuer-feasibility.md),
an owned JDK 21 and Maven 3.9.11. Recorded execution used Temurin 21.0.12.1+1.
Keep the adjacent token-entry lab present; preparation verifies and reuses its
two unchanged control sources without duplicating them in this directory.
From this directory:

```sh
python3 prepare.py /path/to/keycloak-source /path/to/new-native-project native
python3 prepare.py /path/to/keycloak-source /path/to/new-guarded-project guarded
```

Use a new Maven home/cache and explicit credential-free settings mirroring only
Maven Central. Resolve `dependency:build-classpath` with an absolute output path,
then run the adjacent `../entry_guard/verify_sdk.py` against that classpath/cache.
The POM has the same 206 test-classpath coordinates/bytes/license records as the
prior lab; 290 downloaded SDK/build JARs matched the earlier reviewed set.
No new application dependency or production license/security clearance follows.
The two unresolved historical build-helper license declarations and deprecated
test-only native API remain limits.

Use the same explicit Maven settings/cache with `test`, always including
`-DentryGuard.guarded=false`, and select `-DrealmEntry.guarded=false` for the
native project or `true` for the guarded project. Use offline mode after build
plugins are reviewed/cached. The final test JVM disables dynamic agent loading
and uses reflection-only Mockito fixtures. Reports contain expected synthetic
error traces; keep raw reports private. Remove owned projects, cache and source
extraction afterward. Never use `install`, `deploy` or a providers directory.

## Remaining boundary

The fixture cannot establish HTTP filter/body-reader/mapper precedence, real
bootstrap identity/enrollment/storage, all internal/worker callers, SAML/credential
signing, streaming/async/disconnect/serialization cleanup, native SQL/JDBC/HA or
complete entry/writer closure. The proposed A0/A1/A2 layers and every 18-family
source-review obligation remain. The 13 invocation variants are not a new route
universe. All ten native grant declarations, UMA/pre-authorized exceptions,
unknown extensions, browser/broker/SAML/device/CIBA/PAR/OpenID credential/admin
and alternate paths still need complete treatment.

All 22 writer categories, including Client Admin API v2/shared client and native
SCIM feature/provider/model writes, remain mandatory. All old failed oracles,
remaining R1 limits/earlier 503, semantic point-in-time review, R3–R7 and IAM/service
restoration remain open. No existing provider artifact, guard, grant, caller,
schema, migration, dependency, manifest, default or production behavior changed.
No issuer/server/database/existing secret or workload credential/token/data path
was used. [Review](../../realm-entry-review.json) records the exact limits.
