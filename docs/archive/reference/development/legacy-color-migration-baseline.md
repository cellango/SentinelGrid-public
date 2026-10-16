# Legacy Color Migration Closure

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Updated: `2026-03-27`

This document replaces the earlier migration baseline. The legacy `bg-white`, `bg-gray-*`, `text-gray-*`, and `border-gray-*` cleanup is now complete across `frontend/src`.

## Final State

- Previous working baseline after route cleanup: `107 frontend files`
- Current inventory using those legacy color utilities in `frontend/src`: `0 files`
- Compatibility shim removed from: `frontend/src/app/globals.css`
- Guardrail now enforced repo-wide via:
  - `frontend/scripts/check-legacy-color-classes.mjs`

## Verification

- `npm run lint`
- `npm run lint:tokens`

Current `lint:tokens` result:

```text
No legacy color classes found anywhere in frontend/src.
```

## Notes

- The migration sweep included IAM, playbook editor, policy builder, phishing, requests, compliance, AI security, and remaining dashboard workflow surfaces.
- The color guardrail no longer protects only a shortlist of shell/auth files. It now scans all source files under `frontend/src`.
