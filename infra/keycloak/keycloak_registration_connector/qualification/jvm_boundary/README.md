# Owned JDK boundary research probe

Experimental exact-host reference. This fixture qualifies **one trusted JDK-only
control** on macOS 15.5 arm64. The [current containment page](../../../../../docs/architecture/keycloak-lifecycle-containment.md#compatible-jdk-only-control-qualification)
and [result record](../../jvm-boundary-review.json) govern its scope. It grants
no issuer, A0, provider, artifact-resolution or production authority. The full
effective input graph and effect-disabled issuer harness remain NO-GO.

## Inputs and reproduction

`inputs.json` pins the JDK 21.0.12.1+1 archive, **all 459 installed JDK files**,
the source/runner/preparer, OS executables, dyld-support profile and local manual
pages. Obtain the already reviewed toolchain through its recorded provenance;
this fixture never downloads or installs a toolchain. It rejects missing/changed/
extra JDK files, symlinks, unsupported platform, existing output and fixture drift.
Inputs and controller code are trusted review material, not caller authority.

Use a trusted controller Python, without `-O`, from this directory:

```sh
python3 prepare.py /absolute/reviewed/tool-root /private/tmp/sg-owned-jdk-probe-unique
python3 run.py /private/tmp/sg-owned-jdk-probe-unique
```

The tool root must contain the exact pinned archive and installed JDK tree.
Output must be fresh, private and outside source/tools, with no symlink parents.
Profile installation or validation failure stops execution; there is no unguarded
fallback. Apple `sandbox-exec` is deprecated and uses private SBPL policy API.
Use only a previously reviewed launch context; never broaden policy to bypass a
rejected launch. This is not a production isolation mechanism selection.

Preparation writes only the new owned tree. The runner reconstructs the expected
policy instead of trusting a state-provided policy digest. It invokes only the
pinned JDK compiler (`jdk.compiler/com.sun.tools.javac.Main`) under that profile,
with `-proc:none`, `-implicit:none`, empty source/dependency paths and owned class
output. No Maven, extension, plugin or annotation processor runs. The resulting
two class files are hashed, and the app runs with only `java.base`, interpreted
mode, bounded heap/processor settings, owned home/tmp and attach/performance/core
dumps disabled. No JNI, issuer or provider code is added.

Native child `HOME` and Java `-Duser.home` both name the owned home. This is
scoped subprocess configuration; the controller's environment and existing home
remain unchanged. The prior missing-native-home version control still fails
SIGSEGV. The same-policy A/B/A comparison is **-11, 0, -11** when toggling only
that child native-home entry. The pinned JDK source supports the early null-home
failure mechanism; no native crash backtrace was collected. No new dynamic-code,
network, Mach, service, process or file permission was added to fix startup.

## Comparison and retained failure witnesses

The final run passed **51 observations** across unguarded baseline, guarded
closed descriptors, and guarded deliberately inherited stdin modes. Only new
owned canaries and sockets are targeted. The controller binds TCP/Unix sockets
but **never listens**; no existing service, DB, container, credential, token,
host secret or external network destination is contacted.

| Observation | Result and exact limit |
| --- | --- |
| Owned home/environment/work IO | Succeeds. The unguarded macOS runtime adds `__CF_USER_TEXT_ENCODING`; the guarded child has only the four configured entries. No environment values from the parent are copied. |
| Outside-work canary read/stat/write, symlink/hardlink, TCP/Unix connect and socket bind | EPERM in both guarded modes; baseline file/link/bind positives work. Baseline TCP/Unix connect times out/refuses because no socket listens, so no positive delivery comparator exists. |
| Java worker thread | Owned write succeeds; outside-canary read and socket bind get EPERM. This covers one actual thread, not issuer parent/session/CDI/async ownership. |
| ProcessBuilder `/usr/bin/true` | Baseline exits0. Guarded helper path fails with generic `posix_spawn` IOException; do not relabel it as a raw fork/exec errno or every-process-path proof. |
| Java `localhost` lookup | **Succeeds under the guard**, unlike the prior Python probe. It proves neither external DNS access nor resolver/Mach/bootstrap mediation. |
| Inherited stdin negative | Guarded code reads the outside-work canary when FD0 deliberately carries it. Secure stdin is DEVNULL and returns EOF. Policy does not revoke inherited capabilities; the older Python inherited-write witness also remains. |

Twelve preparation/integrity controls also passed: valid output, existing output
preservation, wrong archive, tool-root symlink, fixture drift, output inside
source/tools, forged state/policy, payload drift, prebuilt classes, nonprivate
output and optimized runner. They are separate from the older nine Python-probe
controls and six native-lab controls. Initial new-lab environment/process diagnostic
assumptions were corrected with raw reports retained. No prior native oracle changed.

## Remaining gate

Read-only JDK/System/Library/usr/lib, dyld support (including cryptex scopes),
sysctl reads and the trusted controller remain TCB assumptions. This does not
qualify arbitrary native code, dynamic-code enforcement, external DNS, Mach/
bootstrap/IOKit, service/container/DB/secret mechanisms, resource quotas, side
channels or a complete immutable OS closure. No real provider startup or Quarkus
activation occurred. No 578-case native comparison was rerun.

Return to the open input/harness prerequisite: review the exact offline non-plugin
effective-model resolver inputs and boundary before any model-only check, then
close the full artifact/plugin/processor/provider/classloader/build-step graph
and native effects. Only those gates permit the still-open A0 prototype. A JDK
control, source inventory, classpath list or synthetic receipt cannot authorize it.

Retain `compile.json`, `results.json` and state/policy/input hashes, then remove
only the specific owned output. Never clean shared tools, existing homes/settings/
repositories, credentials or another task's state. No binary or JDK source file
is redistributed by this fixture.
