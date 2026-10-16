# OpenSearch Ingest Pipelines (AWS sources)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Pipelines to normalize AWS sources into ECS-style documents. Apply these to the corresponding index templates/aliases (`{tenant_id}-cloudtrail-*`, `{tenant_id}-net-*`, `{tenant_id}-dns-*`, `{tenant_id}-waf-*`, `{tenant_id}-alerts-*`).

## cloudtrail
```json
{
  "description": "CloudTrail → ECS",
  "processors": [
    { "json": { "field": "message", "target_field": "cloudtrail" } },
    { "set": { "field": "@timestamp", "value": "{{cloudtrail.eventTime}}" } },
    { "set": { "field": "event.action", "value": "{{cloudtrail.eventName}}" } },
    { "set": { "field": "event.provider", "value": "{{cloudtrail.eventSource}}" } },
    { "set": { "field": "event.outcome", "value": "{{cloudtrail.errorCode}}" ,"on_failure": [{"set":{"field":"event.outcome","value":"success"}}]} },
    { "set": { "field": "user.name", "value": "{{cloudtrail.userIdentity.userName}}" } },
    { "set": { "field": "user.id", "value": "{{cloudtrail.userIdentity.arn}}" } },
    { "set": { "field": "source.ip", "value": "{{cloudtrail.sourceIPAddress}}" } },
    { "set": { "field": "cloud.account.id", "value": "{{cloudtrail.userIdentity.accountId}}" } },
    { "set": { "field": "cloud.region", "value": "{{cloudtrail.awsRegion}}" } },
    { "remove": { "field": "message" } }
  ],
  "on_failure": [{ "set": { "field": "tags", "value": ["_ingest_failure"] } }]
}
```

## vpc flow (net)
```json
{
  "description": "VPC Flow → ECS",
  "processors": [
    { "json": { "field": "message", "target_field": "flow" } },
    { "set": { "field": "@timestamp", "value": "{{flow.start}}" } },
    { "set": { "field": "network.transport", "value": "{{flow.protocol}}" } },
    { "set": { "field": "network.bytes", "value": "{{flow.bytes}}" } },
    { "set": { "field": "source.ip", "value": "{{flow.srcaddr}}" } },
    { "set": { "field": "source.port", "value": "{{flow.srcport}}" } },
    { "set": { "field": "destination.ip", "value": "{{flow.dstaddr}}" } },
    { "set": { "field": "destination.port", "value": "{{flow.dstport}}" } },
    { "set": { "field": "cloud.account.id", "value": "{{flow.account-id}}" } },
    { "remove": { "field": "message" } }
  ],
  "on_failure": [{ "set": { "field": "tags", "value": ["_ingest_failure"] } }]
}
```

## route53 resolver dns
```json
{
  "description": "Route53 DNS → ECS",
  "processors": [
    { "json": { "field": "message", "target_field": "dnslog" } },
    { "set": { "field": "@timestamp", "value": "{{dnslog.query_timestamp}}" } },
    { "set": { "field": "dns.question.name", "value": "{{dnslog.query_name}}" } },
    { "set": { "field": "dns.question.type", "value": "{{dnslog.query_type}}" } },
    { "set": { "field": "source.ip", "value": "{{dnslog.srcaddr}}" } },
    { "set": { "field": "cloud.account.id", "value": "{{dnslog.account_id}}" } },
    { "remove": { "field": "message" } }
  ],
  "on_failure": [{ "set": { "field": "tags", "value": ["_ingest_failure"] } }]
}
```

## waf/alb (optional)
```json
{
  "description": "WAF/ALB → ECS",
  "processors": [
    { "json": { "field": "message", "target_field": "waf" } },
    { "set": { "field": "@timestamp", "value": "{{waf.timestamp}}" } },
    { "set": { "field": "http.request.method", "value": "{{waf.httpMethod}}" } },
    { "set": { "field": "url.original", "value": "{{waf.uri}}" } },
    { "set": { "field": "source.ip", "value": "{{waf.clientIp}}" } },
    { "set": { "field": "cloud.account.id", "value": "{{waf.accountId}}" } },
    { "remove": { "field": "message" } }
  ],
  "on_failure": [{ "set": { "field": "tags", "value": ["_ingest_failure"] } }]
}
```

## guardduty (optional)
```json
{
  "description": "GuardDuty → ECS alerts",
  "processors": [
    { "json": { "field": "message", "target_field": "gd" } },
    { "set": { "field": "@timestamp", "value": "{{gd.updatedAt}}" } },
    { "set": { "field": "event.kind", "value": "alert" } },
    { "set": { "field": "event.module", "value": "guardduty" } },
    { "set": { "field": "event.category", "value": "threat" } },
    { "set": { "field": "event.action", "value": "{{gd.type}}" } },
    { "set": { "field": "cloud.account.id", "value": "{{gd.accountId}}" } },
    { "set": { "field": "source.ip", "value": "{{gd.service.action.networkConnectionAction.remoteIpDetails.ipAddressV4}}" } },
    { "remove": { "field": "message" } }
  ],
  "on_failure": [{ "set": { "field": "tags", "value": ["_ingest_failure"] } }]
}
```

> Note: Adjust field paths to match actual log shapes (CloudTrail/Flow/DNS/WAF/GuardDuty JSON). These are reference mappings; finalize with sample payloads. Apply tenant_id via Firehose attributes or an ingest `set` processor if not present. Use ISM/ILM for TTL on these patterns.
