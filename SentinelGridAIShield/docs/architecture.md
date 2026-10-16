# Architecture

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


`SentinelGridAIShield` is a two-service design:

1. a Go gateway that accepts OpenAI-compatible traffic
2. a Python services app that manages metadata, policies, telemetry, and local provider-key lookup

## Data Flow

```text
Client
  -> Gateway (/v1/chat/completions)
  -> Guardrails and policy evaluation
  -> Services internal key lookup
  -> Upstream provider
  -> Gateway telemetry HTTP write
  -> Services event ingest and PostgreSQL commit
  -> Services event query API
  -> Background external SIEM export
```

## Gateway Responsibilities

- parse OpenAI-compatible requests
- require tenant context headers
- evaluate input and output with guardrails hooks
- forward allowed traffic to the selected provider
- emit telemetry

## Services Responsibilities

- store AI app metadata and policies in PostgreSQL
- expose guardrails endpoints
- ingest and query AI events
- expose a local internal endpoint for provider-key retrieval in standalone development
- normalize and export AI events to external SIEM destinations after commit

## Persistence

PostgreSQL stores:

- `ai_apps`
- `ai_policies`
- `ai_events`
- `ai_provider_credentials`

The current standalone stack only requires PostgreSQL.

## Trust Boundaries

- external clients talk to the gateway
- the gateway talks to the services app over an internal token
- provider keys remain on the services side and are fetched on demand for local development

## Current Limitations

- API-key validation for gateway callers is not fully wired in this subtree yet
- provider-key lookup is environment-backed in the standalone path
- advanced control-plane integrations from the larger SentinelGrid platform are intentionally out of scope here
- Splunk HEC is the only live SIEM adapter in the current runtime
- Microsoft Sentinel and QRadar are defined on the same interface, but their adapters are not implemented yet
- `AiToolCall` ingestion is still stubbed on the services side
