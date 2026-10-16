# AI Shield fixtures

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


Sample AI events you can bulk-load into OpenSearch to exercise AI detections (e.g., data leakage, prompt injection, tool misuse).

## Files
- `aishield_events_bulk.ndjson`: bulk-ready action/doc pairs targeting `sg-00000000-0000-0000-0000-000000000000-ai` with:
  - Allowed external request with PII (triggers AI-DATA-LEAKAGE)
  - Blocked prompt injection (triggers AI-PROMPT-INJECTION-DET / AI-JAILBREAK-BURST)
  - Tool call denied (triggers AI-TOOL-CALL-ANOMALY)

## Usage (local dev)
```bash
OPENSEARCH_URL=${OPENSEARCH_URL:-http://localhost:9200}
curl -s -XPOST "$OPENSEARCH_URL/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @scripts/fixtures/ai/aishield_events_bulk.ndjson
```

Then query to verify:
```bash
curl -s "http://localhost:9200/sg-00000000-0000-0000-0000-000000000000-ai/_search?q=event.category:ai&pretty"
```
