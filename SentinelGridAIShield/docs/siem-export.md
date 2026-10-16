# External SIEM Export

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This document defines the standalone `SentinelGridAIShield` interface for pushing AI security telemetry to external SIEM platforms.

## Goals

The standalone package should be able to:

- normalize AI gateway telemetry into a stable event contract
- deliver the same event stream to one or more external SIEMs
- keep destination-specific formatting isolated behind adapters
- give operators a single configuration interface regardless of target SIEM

## Scope

This document defines:

- the normalized event envelope
- the destination configuration contract
- the delivery semantics
- the supported top three SIEM platforms for first-class adapters

This document does not claim the current runtime already includes all adapters.
It defines the standard the standalone system should implement and the interface that operators should configure against.

## Current Runtime Status

What is live now:

- the gateway can send `AiEvent` telemetry to the services API with `TELEMETRY_MODE=http`
- the services API accepts both `org_id` and the gateway's `tenant_id` telemetry field
- services normalizes `AiEvent` records and exports them to Splunk HEC after the DB commit succeeds
- non-UUID `X-App-ID` values remain visible in the normalized raw event payload even though the PostgreSQL summary column only stores UUID-shaped app IDs
- Splunk delivery failures do not block telemetry ingestion

What is not live yet:

- `AiToolCall` export
- Microsoft Sentinel delivery
- IBM QRadar delivery
- a long-running batch worker; current runtime dispatches immediately after each telemetry write

## Top Three SIEM Targets

The recommended first-class adapter set is:

1. Splunk via HTTP Event Collector
2. Microsoft Sentinel via Log Ingestion API and Data Collection Rules
3. IBM QRadar via CEF over Syslog TLS/TCP

These cover the most common enterprise deployment patterns while keeping the interface small enough to implement cleanly.

## Current Telemetry Sources

The current standalone stack already produces:

- `AiEvent`
  LLM interaction telemetry for allowed or blocked chat/completions requests
- `AiToolCall`
  agent-tool invocation telemetry, currently stubbed on the services ingestion side

The gateway is the authoritative producer for these events.

## Normalized Event Envelope

Every destination adapter should accept the same normalized event structure before formatting for the destination platform.

Required top-level fields:

- `event_id`
- `event_type`
- `occurred_at`
- `tenant_id`
- `severity`
- `policy_decision`

Common optional fields:

- `realm`
- `ai_app_id`
- `user_id`
- `provider`
- `model`
- `risk_flags`
- `metrics`
- `previews`
- `labels`
- `raw`

See [siem-event.schema.json](../schemas/siem-event.schema.json) for the formal schema.

## Event Types

Recommended event types:

- `ai.request.allowed`
- `ai.request.blocked`
- `ai.tool_call.allowed`
- `ai.tool_call.blocked`
- `ai.telemetry.health`

## Severity Mapping

Recommended baseline severity mapping:

- `critical`
  blocked high-risk exfiltration, confirmed secret exposure, repeated policy bypass, or explicitly tagged severe cases
- `high`
  prompt injection suspected with block or repeated attempts
- `medium`
  PII or secret detection without block, unusual provider/model usage
- `low`
  allowed request with risk flags or policy overrides
- `info`
  normal allowed requests and health telemetry

## Standard Destination Configuration Interface

Operators should configure SIEM exports through one versioned config file with one or more destinations.

Top-level shape:

```yaml
version: 1
default_delivery:
  mode: batch
  batch_size: 100
  flush_interval_seconds: 5
  retry_max: 3
  timeout_seconds: 10
destinations:
  - name: splunk-primary
    type: splunk_hec
    enabled: true
    transport: http_json
    endpoint: https://splunk.example.com:8088/services/collector
    auth:
      type: bearer
      token_env: SPLUNK_HEC_TOKEN
```

See [siem-export-config.schema.json](../schemas/siem-export-config.schema.json) for the formal schema.

## Destination Fields

Each destination entry supports:

- `name`
  unique local identifier
- `type`
  adapter type such as `splunk_hec`, `microsoft_sentinel_dcr`, or `ibm_qradar_cef_syslog`
- `enabled`
  whether export is active
- `transport`
  transport type such as `http_json`, `syslog_tls`, or `syslog_tcp`
- `endpoint`
  destination URL, host:port, or ingestion endpoint
- `auth`
  destination-specific authentication settings
- `routing`
  destination-specific routing metadata such as index, sourcetype, stream, or table name
- `filters`
  event selection controls
- `format_options`
  output-shaping settings such as `cef_device_vendor` or field inclusion
- `delivery`
  overrides for timeout, retry, and batching

## Filters

Suggested filter controls:

- `include_event_types`
- `exclude_event_types`
- `minimum_severity`
- `include_tenants`
- `exclude_tenants`
- `only_blocked`

## Delivery Semantics

Recommended delivery behavior:

- at-least-once delivery
- retry with bounded exponential backoff
- destination-isolated failures so one broken SIEM does not block another
- post-commit export so the primary telemetry write remains authoritative

Current runtime notes:

- delivery is triggered in a background task after the services DB commit succeeds
- the current implementation sends each ingested event immediately
- `batch_size` and `flush_interval_seconds` remain part of the config contract for a future worker-based batching mode
- dead-letter persistence is not implemented yet; final failures are logged by the services process

## Platform-Specific Adapter Contracts

### Splunk

Adapter type:

- `splunk_hec`

Preferred transport:

- `http_json`

Expected auth:

- bearer token via HEC

Runtime status:

- implemented

Recommended routing fields:

- `index`
- `source`
- `sourcetype`

Payload pattern:

```json
{
  "time": 1735689600,
  "host": "sentinelgrid-aishield",
  "source": "sentinelgrid_ai_shield",
  "sourcetype": "sentinelgrid:ai:event",
  "index": "main",
  "event": {
    "event_id": "...",
    "event_type": "ai.request.blocked",
    "tenant_id": "...",
    "policy_decision": "blocked"
  }
}
```

### Microsoft Sentinel

Adapter type:

- `microsoft_sentinel_dcr`

Preferred transport:

- `http_json`

Expected auth:

- Azure AD application credentials or managed identity for Log Ingestion API

Recommended routing fields:

- `dcr_immutable_id`
- `dce_endpoint`
- `stream_name`
- `table_name`

Recommended output:

- JSON array of normalized events mapped to the custom table columns you define in the Data Collection Rule

Runtime status:

- documented interface only

### IBM QRadar

Adapter type:

- `ibm_qradar_cef_syslog`

Preferred transport:

- `syslog_tls`

Expected auth:

- destination trust via network path and TLS, optionally mutual TLS if deployed behind a relay

Recommended output:

- CEF-formatted lines carrying the normalized event fields in extensions

Runtime status:

- documented interface only

Example:

```text
CEF:0|SentinelGrid|AIShield|1.0|ai.request.blocked|AI request blocked|8|cs1=11111111-1111-1111-1111-111111111111 cs1Label=tenant_id cs2=demo-app cs2Label=ai_app_id cs3=blocked cs3Label=policy_decision msg=Secrets detected in prompt
```

## Recommended Field Mapping

| Normalized field | Splunk | Sentinel | QRadar |
| --- | --- | --- | --- |
| `tenant_id` | event field | custom column | `cs1` |
| `ai_app_id` | event field | custom column | `cs2` |
| `policy_decision` | event field | custom column | `cs3` |
| `provider` | event field | custom column | `deviceCustomString4` equivalent extension |
| `model` | event field | custom column | extension field |
| `risk_flags.has_pii` | event field | custom column | extension field |
| `risk_flags.has_secrets` | event field | custom column | extension field |
| `metrics.tokens_in` | event field | custom column | extension field |
| `metrics.tokens_out` | event field | custom column | extension field |

## Configuration Examples

See:

- [siem-destinations.yaml](../examples/config/siem-destinations.yaml)
- [siem-destination.splunk.yaml](../examples/config/siem-destination.splunk.yaml)
- [siem-destination.sentinel.yaml](../examples/config/siem-destination.sentinel.yaml)
- [siem-destination.qradar.yaml](../examples/config/siem-destination.qradar.yaml)

The combined example keeps Sentinel and QRadar disabled so the shipped config only enables the adapter that exists in runtime today.

## Splunk Enablement Walkthrough

1. Set `TELEMETRY_MODE=http` so the gateway writes telemetry to the services API.
2. Set `SIEM_EXPORT_ENABLED=true`.
3. Set `SIEM_EXPORT_CONFIG_FILE=/app/config/siem-destination.splunk.yaml` in compose, or a local filesystem path if you run services directly.
4. Set `SPLUNK_HEC_TOKEN`.
5. Edit [siem-destination.splunk.yaml](../examples/config/siem-destination.splunk.yaml) for your HEC endpoint and routing values.
6. Restart the `services` and `gateway` processes.
7. Generate a request through the gateway and watch `docker compose logs -f services` for exporter results.

Because export happens after the DB commit, a failed Splunk delivery does not remove or roll back the stored AI event.

## Runtime Integration Point

For the current architecture, the natural fan-out point is the services telemetry ingestion path:

- gateway emits `AiEvent`
- services ingests and persists event summaries
- services invokes one or more SIEM adapters with the normalized event payload

That keeps destination logic out of the gateway and leaves room for batching, retry, and destination-specific throttling in one place as the adapter set grows.

## Implementation Guidance

The code-level interface lives at:

- [siem_export_interface.py](../services/app/services/siem_export_interface.py)
- [siem_event_normalizer.py](../services/app/services/siem_event_normalizer.py)
- [siem_export_config.py](../services/app/services/siem_export_config.py)
- [siem_export_manager.py](../services/app/services/siem_export_manager.py)
- [splunk_hec_exporter.py](../services/app/services/splunk_hec_exporter.py)

That interface defines:

- `NormalizedSiemEvent`
- `SiemDestinationConfig`
- `DeliveryResult`
- `SiemExporter`

## Recommended Next Implementation Steps

1. implement the Microsoft Sentinel adapter on the existing destination contract
2. implement the IBM QRadar CEF/syslog adapter on the same contract
3. extend the same export path to `AiToolCall`
4. add destination validation and health endpoints
5. add a queue or worker layer if you want true batching instead of immediate post-ingest dispatch
