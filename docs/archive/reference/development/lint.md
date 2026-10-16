# Linting Strategy (Platform-wide)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Keep it simple, consistent, and CI-first. We lint in CI using standard toolchains per stack; no tooling baked into runtime containers.

## When
- **Every PR:** run lint/tests to catch issues before merge.
- **Main merges:** same jobs run on main; gate bundle/publish steps on lint/test passing.

## What to run
- **Frontend (Next/React):** `npm run lint` (Next.js lint) + unit tests as configured.
- **Backend (Python services):** service-appropriate lint/tests (e.g., `ruff`/`flake8` + pytest where applicable).
- **OPA policies:** `opa fmt` + `opa test policies/demo` (and other policy dirs). Run in a tooling container (e.g., `openpolicyagent/opa`) during CI, not in runtime.

## Containers
- **Tooling images only:** Use language/tool-specific images in CI (node, python, `openpolicyagent/opa`). Do not embed linters in runtime containers.

## Scope
- Apply the same approach across the platform: frontend, backend services, policies. Add more linters as needed per service, but keep defaults lean to avoid complexity.

## Notes
- Fail-fast on lint/test in CI.
- For OPA, skip if policies are unchanged (optional optimization); otherwise, run fmt/test to gate bundle builds.
