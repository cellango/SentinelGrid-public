# Issuer-core boundary audit prototype

**Opt-in compiler-assisted source inventory.** P1 bounded research is approved in
[ADR 0004](../../../../../docs/architecture/decisions/0004-issuer-core-storage-and-compatibility.md).
This is the first prototype component, not an issuer patch or an implemented
snapshot/fence/grant. The existing provider and current Python guards are unchanged.

The tool verifies the exact upstream 26.8.1 commit archive and every selected
source/service file, copies the verified bytes into an owned temporary snapshot, then uses the JDK
compiler Tree API to parse source without
executing or building vendor classes. It has no network operation, application
import, provider installation or database access. Tool code is original Apache-2.0;
no upstream source, JAR or JDK binary is distributed here.

## Run manually

Use an owned JDK 21 and the exact commit-addressed source archive from the
[feasibility review](../../../../../docs/architecture/keycloak-issuer-feasibility.md).
Extract it separately and retain its root directory. The report path must not
exist; existing output is preserved.

```sh
python3 audit.py --source /path/to/keycloak-source \
  --archive /path/to/pinned-source.tar.gz --java-home /path/to/jdk-21 \
  --output /path/to/new-private-report
```

The CLI has no archive-hash/version override. Wrong archive bytes, changed,
missing, additional or symlinked selected source, parse errors, unknown syntax
selectors, duplicate/missing parsed units and existing report paths are rejected.
The report records method names, source positions, assignment kinds, annotation
names and syntactic call markers. It never emits source literal/argument values,
SQL or credentials. Keep raw path/syntax reports private; this repository records
only bounded aggregate results.

**Exit 2 is expected:** parsing completed, while complete enforcement remains
unproved. Exit 1 indicates an unexpected input/compiler/audit failure. No CLI
result grants a capability or clears R2 implementation, R3/R4 or caller adoption.

## Evidence and limitations

Two final runs produced identical verified manifests, syntax and summaries:
6,441 Java files and 299 service declaration files, across all `src/main/java`
and `src/main/resources/META-INF/services` layouts. This includes testsuite/helper
modules with that layout, separated by module in the report. It is not a deployed
production graph. Ten OAuth grant factory declarations are present; declarations
do not prove which providers are active at runtime.

The inventory reports 56,243 method declarations and 192,464 call expressions.
Markers such as 184 `executeUpdate` calls, 193 `flush` calls and seven
`enableServiceAccount` calls are syntax counts across this scope. They are not
counts of unique effects, database writers, required patches or vulnerabilities.
`remove` can refer to ordinary collections; assignments can be local variables.
Dynamic dispatch, reflection, generated/native code, external stores and runtime
provider selection remain unproved. No symbol resolution or transitive callgraph
is performed, and a method named like a guard is never accepted as enforcement.

The expanded source review identifies concrete additional entry families within
the existing writer categories: feature-gated Client Admin API v2 and native
realm SCIM resource APIs. Their shared client/resource type providers expose
create/update/delete paths. Runtime activation was not measured. They require
mandatory participation or enforceable exclusion, including feature/profile
changes; wrapping only legacy Admin REST handlers cannot establish closure.

All 15 offline controls pass, including provenance drift, added/missing/symlinked
source, invalid Java, duplicate/unknown syntax, nested method attribution, literal
redaction, module separation and existing-output preservation. Run them with:

```sh
SG_CORE_AUDIT_JAVA_HOME=/path/to/jdk-21 python3 -m unittest discover -s . -p test_audit.py -v
```

Without that environment variable, the two compiler controls are explicitly
skipped; a run with skips is not the recorded 15-control qualification.

The [review](../../core-audit-review.json) retains these limits. Remaining R1
instrumentation limits, all old experiments/nine failed gates and R3–R7/ancestor/
IAM/service restoration stay open. The next research unit must test mandatory
native entry-guard hooks against this expanded inventory before any snapshot,
conditional issuance, storage or caller adoption is admitted.
