# Posture subsystem source

Experimental component reference within the [developer source preview](../RELEASE_SCOPE.md).
The canonical frontend is [frontend/](../frontend/); this subsystem's separate UI
is not the primary product console.

Review [services](services/), [analyzers](analyzers/), [shared models](shared/),
and [tests](tests/). The observable/analyzer pattern selects tooling from resource
metadata. Tool declarations do not prove a working adapter or a safe scan.
[Architecture notes](docs/architecture.md) describe this experimental subsystem.

No account connection, cloud scan, model call, standalone startup, database
migration, or remediation operation is supported by this preview. Use root
[check commands](../README.md) and [the dependency review](../docs/release/dependencies.md)
for the resolved review environment. Runtime manifests remain unqualified.
