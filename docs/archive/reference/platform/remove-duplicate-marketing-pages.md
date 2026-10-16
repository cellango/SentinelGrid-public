# Plan: Remove Duplicate Marketing Pages

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Goal: keep the website app as the only source for public/marketing pages; make the frontend app dashboard-only.

## Scope to remove from frontend
- Delete or replace with redirects: `frontend/src/app/(marketing)/page.tsx`, `login/`, `signup/`, `demo/`, `onboarding/`, `privacy/`, `terms/`.
- Keep only dashboard routes under `frontend/src/app/(dashboard)/**` and other app-only routes (e.g., `/siem` redirect).

## Redirects
- Add lightweight redirects in the frontend app for any legacy marketing paths to the website host (`https://localhost:3444` or production `www`).
- Nginx/ingress: route public paths to the website service; route `/dashboard/**` (and app APIs) to the frontend service. Add 301s for legacy marketing paths on the app host → website host.

## Components and shared UI
- If marketing components only exist in `frontend/src/components`, move them to a shared UI package or copy them into `website/components` and delete the duplicates from frontend once pages are removed.
- Update any dashboard links/CTAs that point to in-app marketing routes to use website URLs.

## Tests
- Point marketing UI/Security-in-a-Box smoke tests to the website host.
- Keep dashboard Selenium/UI tests on the frontend host.

## Build/hosting
- Treat website as static/SSR/ISR-only (no auth). Deploy to CDN or its own container on port 3444.
- Keep frontend container focused on the authenticated app (port 3443). Remove marketing build args/env from the frontend image if present.

## Migration checklist
- [ ] Implement redirects for marketing routes in frontend.
- [ ] Move/delete frontend marketing pages.
- [ ] Update links/CTAs to website URLs.
- [ ] Update tests to hit website host for marketing pages.
- [ ] Adjust Nginx/compose routing and add 301s.
- [ ] Clean up unused marketing components from frontend.
