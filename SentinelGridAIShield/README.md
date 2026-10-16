# AI Shield component source

AI Shield's [Apache-2.0 license](LICENSE) is preserved. In this monorepo it is
experimental source within the [developer preview](../RELEASE_SCOPE.md), not a
separately qualified runtime release.

The [Go gateway](gateway/) handles provider-facing requests and policy evaluation;
the [Python services](services/) manage application/policy/event records and related
endpoints. [Examples](examples/) and [component documentation](docs/README.md) are
implementation references, not supported startup or production instructions.

Review tenant-context and API-key validation, provider-key handling, telemetry,
policy enforcement, and SIEM export boundaries. The known missing-configuration
internal-token fallback is recorded in [the credential review](../docs/release/credentials.md).
Do not treat a gateway hook, stub, provider name, or adapter plan as completed control-plane
integration. Model/provider calls and customer telemetry are excluded from supported
preview checks. Root [security reporting](../SECURITY.md) and
[release evidence](../docs/release/review.md) govern this source snapshot.
