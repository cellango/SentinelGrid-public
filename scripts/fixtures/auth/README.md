# Auth fixtures

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


- `keycloak_login_error.ndjson`: raw Keycloak console JSON log lines (docker log format) that flow through the `keycloak-auth-pipeline` into `sg-*-auth-*`. If you bulk index this, add an action line and pass the pipeline.
- `keycloak_login_error_bulk.ndjson`: ready-to-bulk file (action+doc pairs) targeting `sg-00000000-0000-0000-0000-000000000000-auth`; use with `?pipeline=keycloak-auth-pipeline`.

## Quick usage (local dev)

1) Ensure the ingest pipeline exists:
```bash
OPENSEARCH_URL=http://localhost:9200 backend/services/ingestion_service/scripts/apply_pipelines.sh
```

2) Bulk-load the sample login errors through the pipeline:
```bash
curl -s -XPOST "http://localhost:9200/_bulk?pipeline=keycloak-auth-pipeline" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @scripts/fixtures/auth/keycloak_login_error_bulk.ndjson
```

3) Verify parsed fields:
```bash
curl -s "http://localhost:9200/sg-00000000-0000-0000-0000-000000000000-auth/_search?q=event.action:LOGIN_ERROR&pretty"
```
