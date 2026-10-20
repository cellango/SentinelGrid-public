# Owned OS boundary research probe

Experimental reference. This exact-host probe tests trusted, harmless Python
sentinels. It grants no issuer, provider, build, A0 or production authority. The
[current containment review](../../../../../docs/architecture/keycloak-lifecycle-containment.md#os-boundary-and-executable-input-prerequisite-result)
and [machine-readable record](../../harness-boundary-review.json) describe its
scope and the separate failed JVM startup control. Historical native labs are
unchanged and were not rerun.

## Exact inputs and reproduction

The fixture pins macOS 15.5 arm64, the Python 3.14.4 **app executable**, its
framework library, OS executables, `dyld-support.sb` and local manual pages in
`inputs.json`. The Python launcher spawns another image and is rejected here.
The controller and installed read-only Python/OS trees are trusted inputs, not
a complete immutable executable or license/security closure. Apple documents
`sandbox-exec` as deprecated; the SBPL policy is a private OS API, used only for
this host-specific experiment.

Run from this directory with a trusted controller Python, without optimized
`-O` mode. Supply the exact reviewed app image and a new absolute owned output
directory outside the fixture/runtime, with no symlink parents:

```sh
CONTROL_PYTHON=/absolute/path/to/reviewed/Python.app/Contents/MacOS/Python
python3 prepare.py "$CONTROL_PYTHON" /private/tmp/sg-owned-os-boundary-unique
python3 run.py /private/tmp/sg-owned-os-boundary-unique
```

Input drift, unsupported platform, existing output, policy replacement or failure
to install the policy must stop execution. The runner reconstructs the expected
policy from trusted fixture code; a caller-supplied state digest cannot authorize
a broader policy. There is no unguarded fallback. In the original nested tool
sandbox, profile installation failed with exit 71/EPERM. The separately reviewed
host launch control succeeded; that launch alone proves no resource denials.
Do not bypass a rejected launch by changing the deny policy.

`prepare.py` writes only the fresh owned tree. `run.py` captures three modes in
`results.json`: unguarded baseline, guarded with closed descriptors, and an
intentional guarded inherited-descriptor negative control. Baseline effects
touch only new synthetic canaries, owned sockets and harmless child controls.
The controller binds owned TCP/Unix sockets but **never listens**. No existing
database, service, container socket, credential, host secret or external network
target is contacted. The script does not import Maven, Keycloak or providers.

## Observed comparison and negative witness

The reproducible run passed **42 expected observations** across three modes:

| Probe | Closed-descriptor guard | Evidence limit |
| --- | --- | --- |
| Owned work file read/write | Allowed | Positive control for this payload. |
| Outside-work synthetic canary read/stat/write, symlink read, hardlink create | EPERM | Only owned new paths were tested; no real secret was read. |
| Owned loopback TCP connect, socket bind and Unix connect | EPERM | Unguarded connect timed out/refused because targets never listen; no positive network-delivery control. |
| Localhost name lookup | `gaierror` | Does not prove external DNS or arbitrary Mach/bootstrap service mediation. |
| Fork and unapproved `/usr/bin/true` execution | EPERM | Does not qualify every process/container/OS service mechanism. |
| Explicit canary descriptor | EBADF, canary unchanged | Requires `close_fds=True`, empty `pass_fds` and owned stdio. |

**The intentional inherited-descriptor mode writes the outside-work canary
successfully under the same policy.** Policy installation cannot revoke a
capability already inherited through that descriptor. This failure witness is
required evidence; do not remove it or claim that the policy alone closes effects.
Only the baseline and intentional negative inherit the explicit owned canary FD.

Nine preparation/integrity controls were also checked on private owned fixture
copies: valid output, preserving existing output, wrong runtime hash, runtime
symlink, fixture drift, output inside source/runtime, forged state/policy digest,
and optimized runner rejection. They test the recipe's inputs and output bounds.
They are separate from the six inherited native-lab controls.

## Qualification stop

The policy permits read-only Python/System/Library/usr/lib inputs and sysctl reads.
Those are controller TCB assumptions, not arbitrary-code containment proof.
External DNS, Mach/bootstrap/IOKit/service/container/DB interactions, resource
limits, side channels, whole runtime immutability and JVM/native-provider behavior
remain unqualified. An additional archive-revalidated JDK version-only attempt
under a separate deny policy exited **-11 (SIGSEGV)** before any output; its cause
is unknown. No Maven, model resolver, plugin, processor, Quarkus augmentation,
issuer build or native candidate ran. A Python result cannot qualify that JVM.

The full effective executable graph and effect-disabled harness remain **NO-GO**.
First qualify a compatible JVM boundary with reviewed inputs and meaningful
owned negative controls, then complete offline effective-model/artifact/provider
closure before returning to the still-open A0 prototype. No effect permission
may be widened merely to get a passing startup. Preserve raw failed results.

After retaining the reports, remove only the specific owned output tree you
created. Never clean shared caches, existing homes/settings/repositories or
another task's files. No runtime/default/provider or production dependency is
installed or adopted by this fixture.
