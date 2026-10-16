# Ingest Endpoint Contract (AWS one-click / Firehose HTTP)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**URL:** `https://<INGEST_HOST>/ingest/events`

**Method:** `POST`

**Headers:**
- `Content-Type: application/json`
- `X-Tenant-ID: <TENANT_UUID>`
- `Authorization: Bearer <token>` (optional; required only if your deployment enforces auth)

**Body schema:**
```json
{
  "tenant_id": "optional-tenant-override",
  "events": [
    {
      "event_type": "cloudtrail" | "vpc_flow" | "dns" | "waf" | "guardduty" | "...",
      "source": "aws_cloudtrail" | "vpc_flow" | "route53_resolver" | "waf" | "guardduty" | "...",
      "timestamp": "ISO8601 UTC",
      "raw_data": { /* vendor JSON for the event */ },
      "metadata": { /* optional */ }
    }
  ]
}
```

**Notes:**
- `X-Tenant-ID` is required; `tenant_id` in the body is optional and used as an override.
- If `timestamp` is omitted, ingestion will use `raw_data.eventTime` (if present) or current time.
- Auto-routing for AWS sources:
  - `cloudtrail` → `*-cloudtrail` with `pipeline-cloudtrail`
  - `vpc_flow`   → `*-net` with `pipeline-vpcflow`
  - `dns`        → `*-dns` with `pipeline-dns`
  - `waf`        → `*-waf` with `pipeline-waf`
  - `guardduty`  → `*-alerts` with `pipeline-guardduty`
- Pipelines map to ECS-style fields; index templates are applied for the above patterns.
- Test data: use a `-test` index suffix and/or add `tags:["test"]` in payloads to isolate.

**Firehose HTTP config:**
- Endpoint URL: `https://<INGEST_HOST>/ingest/events`
- Headers: `X-Tenant-ID=<TENANT_UUID>`, `Content-Type=application/json`, optionally `Authorization: Bearer <token>`
- Encoding: GZIP payloads OK; typical buffering 1MB/60s.

**Example (curl):**
```bash
TENANT="c6d82f67-36f1-4c7e-af66-d1333e45cde7"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > /tmp/cloudtrail.json <<'JSON'
{
  "events": [
    {
      "event_type": "cloudtrail",
      "source": "aws_cloudtrail",
      "timestamp": "REPLACE_NOW",
      "raw_data": {
        "eventTime": "REPLACE_NOW",
        "eventName": "ConsoleLogin",
        "eventSource": "signin.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "awsRegion": "us-east-1",
        "userIdentity": {
          "userName": "alice",
          "arn": "arn:aws:iam::123456789012:user/alice",
          "accountId": "123456789012"
        },
        "errorCode": null
      }
    }
  ]
}
JSON
sed -i.bak "s/REPLACE_NOW/$NOW/g" /tmp/cloudtrail.json
curl -X POST "https://<INGEST_HOST>/ingest/events" \
  -H "X-Tenant-ID: $TENANT" \
  -H "Content-Type: application/json" \
  --data @/tmp/cloudtrail.json
```
