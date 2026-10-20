# Offline selected-model research check

Experimental reference. This recipe qualifies a **bounded Maven model-library
API check**, outside Maven CLI and without artifact/plugin execution. The
[current containment page](../../../../../docs/architecture/keycloak-lifecycle-containment.md#offline-selected-model-prerequisite-qualification)
and [result record](../../offline-model-review.json) define its scope. Full
artifact/provider inputs, issuer isolation and A0 remain NO-GO. Model success
cannot serve as a build/admission receipt.

## Exact inputs and reproduction

`inputs.json` pins six model libraries from the reviewed Maven 3.9.11 archive,
263 previously reviewed POMs and this fixture. It reuses the hash-pinned sibling
[`jvm_boundary` preparer](../jvm_boundary/README.md), which validates the exact
macOS 15.5 arm64 platform, JDK archive/all 459 installed files and OS policy inputs.
The separate archive review also revalidates all 96 Maven files. No download,
installer, existing Maven home/settings/repository, credentials or automatic
dependency resolution is used. Only those six JARs enter the execution classpath;
Maven core/CLI/transport/plugin/Guice/Sisu/ASM runtimes are excluded. The selected
425-class static inventory is not a complete dynamic call graph. Annotation-only
Inject/Sisu descriptors are not interpreted by the explicitly constructed path;
missing executable classes fail without classpath expansion.

Use a trusted controller Python without optimized `-O`, from this directory:

```sh
python3 prepare.py /absolute/reviewed/tool-root /absolute/private/reviewed-POM-root /private/tmp/sg-offline-model-unique
python3 run.py /private/tmp/sg-offline-model-unique
```

The tool root contains the existing reviewed JDK/Maven trees. The owner-private
POM root must contain the exact manifest paths/bytes, not an existing Maven cache.
The fixture requires its unchanged sibling JDK helper in the repository layout.
Output is fresh/private and outside source/tools/POM inputs, with no symlink
parents. Inputs are copied to a separate read-only subtree. The trusted fixture
reconstructs every copied hash and policy; caller state cannot authorize a changed
JAR, POM table or broader policy. Unsupported inputs or policy installation deny;
there is no unguarded fallback. Retain reports before removing only owned output.

## Model and effect boundary

The guard is installed before JVM startup. The same core deny policy adds only a
read-only **task-owned input** subtree. It grants no new external network/Mach/
service/process/unowned-file access. Owned work remains writable. Native child
home matches owned Java home, descriptors are closed, stdin is DEVNULL and the
environment contains only four owned/configured entries. Before constructing
the model builder, controls verify outside-canary read, input write and socket
bind denial, owned work write and stdin EOF. No listener or real service is used.

Compilation uses the pinned JDK compiler with `-proc:none`, `-implicit:none` and
empty source path. Execution limits JDK modules to `java.base,java.xml`. Class
origin logs must resolve to the JDK, exact six JARs or owned harness; generated
lambda origins are followed to their reviewed defining-class origins. This is
evidence for this run, not authority for unknown code.

The harness explicitly constructs the [model factory](https://github.com/apache/maven/blob/3e54c93a704957b63ee3494413a2b544fd3d825b/maven-model-builder/src/main/java/org/apache/maven/model/building/DefaultModelBuilderFactory.java).
It uses plain byte-array `ModelSource` rather than file/URL/`ModelSource2`, so
relative-parent lookup cannot search the filesystem. Every POM is checked for
hash, declared coordinate and forbidden DTD/entities before model parsing. JDK
XML parsing disables external DTD/schema access. The resolver only maps exact
reviewed coordinates to checked bytes, rejects ranges/missing/foreign inputs,
and records repository IDs without using URLs. Request system/user properties
are explicit empty maps; there is no settings/workspace listener or automatic
environment/file/OS/JDK/default-profile activation. `processPlugins=false` leaves
plugin declarations as data, with no CLI, extension, processor or plugin run.

## Observed results and retained failures

**15 model/boundary assertions and 16 preparation/integrity controls pass.** The
checks cover synthetic parent/BOM version inheritance, explicit versus automatic
profile selection, ignored repository callbacks, missing/ranged/foreign/digest-
altered/DTD input denials, copied-input/policy/state forgery, aliases, output
bounds, prebuilt classes and optimized runner rejection.

All five selected native models succeed with **explicit `crypto-default` and
`upstream-adapters` profiles**. This is an upstream non-FIPS model plan, not proof
of default production/native build/profile equivalence or a feature retirement.
The root `upstream-adapters` profile supplies required EE coordinates. The earlier
crypto-only selection failed all five models; that incomplete-profile failure
remains an expected negative. Initial Java interface-return-type compile and
generated class-origin validation corrections are retained privately.

| Model | Direct dependency declarations | Dependency-management entries |
| --- | ---: | ---: |
| Native root parent | 0 | 2419 |
| Quarkus parent | 0 | 2419 |
| Native runtime | 102 | 2419 |
| Native deployment | 26 | 2419 |
| Native server app | 6 | 2419 |

All 134 direct version values are interpolated. Effective XML, dependency tuples,
resolver requests and full class-origin logs remain private review evidence;
the public JSON records hashes and selected declarations. These outputs are not
a mediated transitive artifact graph, executable provider list or source-output
proof. No new JAR, Quarkus augmentation, native build, issuer/provider operation
or A0 candidate ran. The 578 native cases and six controls remain inherited and unchanged.

## Limits and next gate

Maven `ModelSource` generates four deprecation warnings; the older helper-license/
deprecated API limits remain. Apache declarations and archive notices (including
Indiana parser attribution) cover the reviewed research inputs, not full binary/
transitive licensing, CVE/PGP/SBOM/security or distribution clearance. The 263 POM
metadata/192publisherchecksums/71missing checksums and133plugin-coordinate pool
remain separate evidence. No library, raw POM or upstream source is redistributed.

Trusted controller/JDK/system/cryptex/sysctl inputs and deprecated private Apple
SBPL remain assumptions. External DNS, Mach/bootstrap/IOKit, arbitrary native,
service/container/DB/secret/resource/sidechannel mediation is unqualified. The old
Python/JVM inherited-capability witnesses and Java localhost success remain;
neither model success nor this policy makes those gaps disappear.

Next use the five explicit models to review and close selected transitive binary,
plugin/processor/extension/provider/classloader/build-step inputs and effects.
Review every new coordinate/hash/license/provenance/security limit before use;
never auto-fetch from POM repositories. Both full input and issuer-isolation gates
must pass before the same open A0 native prototype resumes. All earlier lifecycle,
writer, cleanup, durability and Task6capability-restoration requirements remain.
