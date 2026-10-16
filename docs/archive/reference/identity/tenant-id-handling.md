# Tenant ID vs. Slug Handling (Gateway Edge)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


- **Programmatic traffic:** Always uses tenant UUIDs end-to-end to enforce hard isolation.
- **Customer-facing convenience:** `tenant_slug` is accepted only at the API gateway edge. The gateway resolves slug → UUID (optionally scoped by realm) and forwards only UUIDs to downstream services.
- **Enforcement:** If slug does not map to the authenticated tenant/realm, the gateway returns 403; unknown slug returns 404. Services remain UUID-only.
- **Caching:** Gateway keeps a short in-memory cache (TTL ~60s) for slug → UUID to avoid repeated DB lookups.

## Quick smoke (gateway → orchestrator)
- Prereq: obtain a valid access token for the target tenant (e.g., demo tenant UUID `ff1c2b60-1fd6-46d1-8458-b0484f5d58f8`, slug `demo`).
- UUID path: `curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:3443/api/v1/orchestrator/scans/status?limit=5"`
- Slug path: `curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:3443/api/v1/orchestrator/scans/status?limit=5&tenant_slug=demo"`
- Expect 200 with identical results. Any 403/404 on the slug path indicates mismatch or unknown slug; downstream isolation is preserved.
