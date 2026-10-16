# Frontend ownership and route layout

Status: current source reference, October 15, 2026. The main application is
[frontend](../../frontend/). This consolidates the former website-archival and
frontend-migration documents.

| Tree | Role |
| --- | --- |
| [frontend/src/app](../../frontend/src/app/) | Canonical Next.js product and marketing route tree |
| `frontend/src/app/(marketing)/` | Marketing prototypes, login/signup, and onboarding routes |
| `frontend/src/app/(dashboard)/dashboard/` | Main product UI; intended URL prefix `/dashboard/` |
| [frontend/src/components](../../frontend/src/components/) | Shared console components |
| [frontend/src/lib](../../frontend/src/lib/) | API clients, auth helpers, and product/story types |
| [website](../../website/) | Archived reference app; no new product work |
| [Posture frontend](../../SentinelGridPostureAgent/frontend/) | Separate experimental UI; not the primary console |

Route groups do not appear in URLs. Legacy aliases may remain in source; inspect
middleware, route handlers, and callers before changing them. Directory membership
alone does not prove authorization. Use [the identity source map](../reference/identity.md)
for auth review.

The supported frontend command is the focused test command in the root
[README](../../README.md), using Node.js 22 and the committed lockfile with dependency
lifecycle scripts disabled. Full build, server startup, billing, signup provisioning,
and backend/provider integration are unqualified. Marketing routes are labeled as
experimental prototypes; they are not a hosted offer or a release certification.
