# Model validation-context diagnostic

Experimental reference. This separate diagnostic reviews the two model blockers
from the [265-target research recipe](../offline_child_models/README.md), with
**457 pinned POMs, two target GAVs and four immutable comparisons**. The
[result record](../../model-context-review.json) and
[current containment page](../../../../../docs/architecture/keycloak-lifecycle-containment.md#child-model-blocker-and-validation-context-review)
record three successful models and one retained strict denial. All **17 model/
boundary assertions and 22 integrity controls pass**. Full transitive inputs,
actual descriptor/project processing, native issuer isolation and A0 remain open.

## Source-backed scope

At [Maven 3.9.11's pinned source](https://github.com/apache/maven/blob/3e54c93a704957b63ee3494413a2b544fd3d825b/maven-resolver-provider/src/main/java/org/apache/maven/repository/internal/DefaultArtifactDescriptorReader.java#L269),
the dependency-descriptor reader requests `MINIMAL` model validation and disables
plugin processing. Its actual pipeline also has session properties, cache,
repository resolution and file sources. **None of that pipeline runs here.**
Only its validation-level dimension is compared using our checked byte sources,
exact offline resolver, empty request properties and explicit profile policy.

The [project request default](https://github.com/apache/maven/blob/3e54c93a704957b63ee3494413a2b544fd3d825b/maven-core/src/main/java/org/apache/maven/project/DefaultProjectBuildingRequest.java#L48)
is `STRICT`; the [model request constants](https://github.com/apache/maven/blob/3e54c93a704957b63ee3494413a2b544fd3d825b/maven-model-builder/src/main/java/org/apache/maven/model/building/ModelBuildingRequest.java#L63)
map that alias to `MAVEN_3_0` (30) in this version. Our earlier research used
`MAVEN_3_1` (31). That earlier level and both original fixtures/evidence remain
unchanged. The new diagnostic permits levels 30/0 only for the exact JCTools GAV
in its fixed case matrix. No caller argument or state selects a validation policy.

The raw JCTools POM still contains two main-build `maven-bundle-plugin` declarations.
The [normalizer](https://github.com/apache/maven/blob/3e54c93a704957b63ee3494413a2b544fd3d825b/maven-model-builder/src/main/java/org/apache/maven/model/normalization/DefaultModelNormalizer.java#L51)
merges duplicate plugin data into the effective model. Raw declaration hashes and
both declarations remain evidence. A normalized single entry does not prove that
a plugin is excluded, harmless, executable or compatible with a real build.

## Exact inputs and reproduction

`inputs.json` pins the prior 456-POM corpus plus the newly reviewed
`org.junit:junit-bom:5.12.2`. The BOM has no parent or root imported BOM, matches its
publisher SHA512 and declares EPL v2.0. Its addition is POM-only metadata, not a new
JUnit binary dependency, security or distribution clearance. Surefire's parent
overrides `versions.junit5` to 5.12.2; its inherited Maven-parent import uses that
child value rather than the parent's 5.14.2 default. This explains why per-POM
literal ancestry did not cover the prior child-context request.

Use the same exact macOS 15.5 arm64 platform, reviewed JDK/Maven archive trees,
six model/Plexus libraries and unchanged sibling `jvm_boundary` helper as the
earlier model recipes. Construct a fresh private curated metadata root with all
457 canonical paths/bytes, retaining 46 source POMs and 411 published metadata
POMs with source-first provenance. It is not an existing Maven cache/repository.
No downloader, installer, proxy/auth/settings, automatic resolution or new library
is used by the recipe. From this directory with a trusted non-optimized Python:

```sh
python3 prepare.py /absolute/reviewed/tool-root /absolute/curated-POM-root /private/tmp/sg-model-context-unique
python3 run.py /private/tmp/sg-model-context-unique
```

Trusted reviewed recipe/controller identities are bootstrap authority. Fixed
digests protect POM/library/target/context tables; edited state or a new manifest
cannot authorize changed code or policy. Paths reject aliases/symlink parents,
input/output overlap and existing output. Copied inputs are read-only and must
remain byte-identical. Retain reports before removing only owned output.

The unchanged deny policy, closed descriptors/stdin DEVNULL, minimal environment,
owned matching native/Java home, outside-read/input-write/socket-bind denials,
owned write and class-origin checks remain. Compilation uses the pinned JDK,
`--release 21`/`-proc:none`/`-implicit:none`, empty source path and six libraries.
No CLI/core/transports/plugin/Guice/Sisu/ASM runtime is added. The model modules,
90-second compiler/600-second batch/128 MiB heap/8 MiB file/256 MiB total output
bounds are unchanged. Unknown inputs, profiles, ranges or contexts deny without
automatic fetch. The two new model controls retain Surefire's missing-BOM denial
and deny a foreign target/context. Two new integrity controls reject manifest
rewrites of the context target or strict witness. All earlier controls remain.

## Observed comparisons and limits

| Case | Model validation | Result |
| --- | --- | --- |
| Surefire 3.5.6 with reviewed BOM | Prior research `MAVEN_3_1` (31) | Success; vintage-engine version resolves to 5.12.2. |
| JCTools 4.0.5 strict witness | Prior research `MAVEN_3_1` (31) | Expected duplicate-plugin rejection, retained. |
| JCTools project-default comparison | `STRICT=MAVEN_3_0` (30) | Success with duplicate-plugin warning retained. |
| JCTools descriptor-validation comparison | `MINIMAL` (0) | Success for model data; no full descriptor-reader equivalence. |

No global level was lowered, raw POM edited, target removed or strict witness
discarded. Both successful JCTools effective models have one normalized bundle
plugin entry; the raw POM remains two. Model data does not establish complete
plugin configuration merge/reach, binary safety or actual execution. Four exact-
commit official Maven source files support the comparison; hashes/anchors are
recorded. Raw sources, POMs, XML, ordered tuples, provenance and diagnostics stay
private. The earlier 265-target run is historical and was not rerun or rewritten;
this does not claim all 265 strict cases now pass.

Next prepare a role-aware model/edge plan and exact transitive frontier using the
prior successful models and these scoped data results. Preserve each model's
validation/profile/parent/BOM provenance, raw duplicates, all realms/scopes/types/
classifiers/optional/exclusions and path-specific mediation questions. Review every
newly missing input before use; no inventory can act as a complete executable lock.

No new binary/JAR or executable library, actual project builder/descriptor reader,
Maven CLI/plugin/extension/annotation processor/Node/Quarkus augmentation, native
issuer/provider or A0 candidate ran. Four ModelSource deprecation warnings and all
prior license/checksum/security/CVE/PGP/SBOM/distribution/source-output limits remain.
The 578 native cases/six controls, inherited FD/stdin/localhost witnesses and trusted
OS/JDK/controller/cryptex/sysctl/private Apple API/Mach/DNS/service/container/DB/
secret/native/resource/sidechannel limits remain. All lifecycle/writer/cleanup/
durability/tenant/caller/capability-restoration gates remain. Both full input and
independent native issuer-isolation gates must pass before the same open A0 resumes.
