# Expanded offline child-model research check

Experimental reference. This recipe qualifies a bounded model-library API input
and owned effects boundary for **456 POMs and 265 targets**. It uses six reviewed
model/Plexus libraries and the pinned JDK, outside Maven CLI. The
[current containment review](../../../../../docs/architecture/keycloak-lifecycle-containment.md#expanded-offline-child-model-qualification)
and [result record](../../offline-child-model-review.json) define the evidence.
**263 models succeed and two remain NO-GO. Full executable inputs, native issuer
isolation and A0 are unqualified.** No build/admission receipt follows.

## Exact inputs and reproduction

The original sibling [`offline_model`](../offline_model/README.md) fixture and its
263-POM/five-model evidence remain unchanged. This separate recipe pins the expanded
456-POM manifest and exact 265-target allowlist in `inputs.json`. Model inputs use
46 pinned source POMs and 410 published metadata POMs; five source/published overlaps
have identical bytes and retain both origins. The
[metadata review](../../selected-metadata-review.json) records source identity,
parent ancestry, license declarations and publisher-checksum gaps. Raw POMs and
binaries are not redistributed. Model success cannot clear their license/security/
CVE/PGP/SBOM/distribution or source-output limits.

Prepare a new private owner-controlled curated POM root with the exact canonical
paths/bytes in the manifest, using the reviewed source-first provenance. Use the
existing reviewed tool root containing the pinned JDK/Maven archive trees. This
is not an existing Maven cache/home/repository. No downloader, installer, automatic
resolver, credentials, proxy or settings is used. From this directory, with a
trusted non-optimized controller Python and the unchanged sibling `jvm_boundary`:

```sh
python3 prepare.py /absolute/reviewed/tool-root /absolute/curated-POM-root /private/tmp/sg-offline-child-model-unique
python3 run.py /private/tmp/sg-offline-child-model-unique
```

The exact platform is macOS 15.5 arm64. The preparer validates all 459 JDK files,
archive and pinned OS inputs; the separate archive review revalidates all 96 Maven
files. Only six exact libraries enter the classpath. CLI/core/transports/plugin/
Guice/Sisu/ASM runtimes are excluded. Trusted reviewed recipe/controller identities
are the bootstrap authority; an edited manifest cannot authorize edited code.
The recipe fixes independent POM/library/target-table digests before preparation.
It rejects changed target count/order/duplicates or pin tables before output.
The input root/output cannot use symlink parents or overlap fixture/tools/metadata;
existing output is preserved. Only fresh owned output may be removed after reports.

## Boundary and observed results

The effect policy and resolver/profile functions are unchanged from the bounded
five-model recipe. Compiler and model JVMs run under the same deny policy, with
closed inherited descriptors, stdin DEVNULL, minimal environment, owned matching
native/Java home and read-only copied inputs. Before constructing the builder,
controls verify outside-canary read, copied-input write and socket-bind denial,
owned work write and stdin EOF. No listener or real service is used. Trusted
definitions reconstruct every copied hash/policy; forged state is not authority.

The compiler uses `--release 21`, `-proc:none`, `-implicit:none`, empty source path
and six libraries. Model execution limits modules to `java.base,java.xml`. Class
origins must resolve to JDK/six pinned JARs/owned code, including verified defining-
class aliases for generated lambdas. Copied inputs remain unchanged. The compiler
timeout is 90 seconds and the 265-target model-only batch limit is 600 seconds;
heap remains 128 MiB. Unique ordinal output IDs use CREATE_NEW, with 8 MiB per
target file and 256 MiB total target-output bounds. These bounds add no permission.

**All 15 model/boundary assertions and 20 integrity controls pass.** The original
16 preparation controls remain, with four new target/pin-manifest tampering checks.
The model API uses explicit factory construction, checked byte `ModelSource`
rather than `ModelSource2`, exact offline hash/coordinate lookup, forbidden local
model locator, empty request properties/fixed build time and plugin processing off.
Repository callbacks record IDs only; no URL transport/settings/workspace/listener
or automatic host/file/OS/JDK/default profile activation is available.

Every target uses explicit `crypto-default` plus `upstream-adapters` and the selected
`MAVEN_3_1` validation level. This is a research plan across several target roles,
not default/native/production or dependency-descriptor context equivalence. The
crypto-only incomplete-profile negative remains. No capability is retired.

All 265 outcomes are recorded: **263 success, two NO-GO**. Successful models contain
2,054 ordered direct declarations and 216,965 managed-entry occurrences, with no
unresolved direct dependency scalar properties. Those repeated contextual entries
are not unique mediated dependencies. Raw effective XML, ordered tuples, parent/
explicit-profile provenance, 1,114 resolver requests and class logs remain private;
the public record contains per-target outcomes/counts/hashes and exact blockers.
The model/provenance accessors were statically checked in the pinned library.

## Unresolved models and next gate

| Target | Observed failure |
| --- | --- |
| `org.apache.maven.plugins:maven-surefire-plugin:3.5.6` | Child context requests unpinned `org.junit:junit-bom:5.12.2`; its missing import also leaves the vintage-engine version unresolved. No automatic fetch occurred. |
| `org.jctools:jctools-core:4.0.5` | The pinned raw POM has two main-build declarations of `org.apache.felix:maven-bundle-plugin`; the selected validation level rejects the duplicate. |

The JCTools result is a compatibility failure under this selected model-validation
context, not proof about binary safety or validity. Next review root/project versus
dependency-descriptor validation semantics using primary Maven evidence. Preserve
the strict failure and raw POM bytes; do not edit the POM, silently drop the target
or lower validation merely for a pass. Review the missing JUnit BOM and ancestry
before any later fixed credential-free metadata retrieval. Static root-ancestry
closure did not establish all child-context interpolated imports.

Four ModelSource deprecation warnings and prior helper/license/security limits
remain. No new library/JAR/network fetch, Maven CLI/plugin/extension/processor/Node/
Quarkus augmentation, native issuer/provider operation or A0 candidate ran. The
578 native cases and six controls remain inherited and unchanged. Provided/test/
optional scope, service/annotation names and old artifact presence do not prove
selection or exclusion. Both native processors, generated descriptor/index,
source/bootstrap/frontend/default lifecycle, devservices/container/classloader/
provider/early initialization and actual source-built output effects remain gates.

The OS/JDK/controller/cryptex/sysctl/private Apple API trust limits, inherited FD/
stdin witnesses, Java localhost success and unqualified arbitrary-native/Mach/
bootstrap/IOKit/DNS/service/container/DB/secret/resource/sidechannel scope remain.
Models do not qualify those effects. All lifecycle/writer/cleanup/durability/
compatibility/tenant/caller and capability-restoration requirements remain. Only
both full input and native issuer-isolation gates permit the open A0 prototype.
