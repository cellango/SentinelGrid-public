# Configuration

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This document describes the main environment variables and runtime assumptions in the standalone package.

## Services Variables

### `DB_URL`

PostgreSQL connection string used by the FastAPI services app.

Default in compose:

```bash
postgresql://postgres:postgres@postgres:5432/sentinelgrid_ai_shield
```

### `INTERNAL_SERVICE_TOKEN`

Shared token used between the gateway and the services app for internal provider-key fetches.
Change this outside local development.

### `SIEM_EXPORT_ENABLED`

Enables the external SIEM export pipeline in the services layer.
When enabled, telemetry is normalized after the DB commit and sent to configured destinations in a background task.

### `SIEM_EXPORT_CONFIG_FILE`

Path to the SIEM destination configuration file that follows:

- [siem-export-config.schema.json](../schemas/siem-export-config.schema.json)

In the compose flow, [../examples/config](../examples/config) is mounted into the services container at `/app/config`.

### `SIEM_EXPORT_BATCH_SIZE`

Default batch size merged into the YAML config when a destination does not override it.
The current runtime dispatches events immediately after ingestion rather than through a long-running batch worker, so this is a forward-compatible default.

### `SIEM_EXPORT_TIMEOUT_SECONDS`

Default timeout merged into destination delivery settings.

### `SIEM_EXPORT_RETRY_MAX`

Default retry limit merged into destination delivery settings.

### `SPLUNK_HEC_TOKEN`

Bearer token used by the implemented Splunk HEC exporter when your destination config references `token_env: SPLUNK_HEC_TOKEN`.

### `PLATFORM_ALERT_INGEST_ENABLED`

When `true`, the services app forwards risky AI telemetry into the main SentinelGrid platform after the local DB commit succeeds.

Use this when `SentinelGridAIShield` is deployed as the AI-runtime-security layer for the broader SentinelGrid platform and you want AI alerts to show up in the main incident and queue workflow.

### `PLATFORM_API_URL`

Base URL of the main SentinelGrid platform API that accepts internal AI Shield alert ingest calls.

Default:

```bash
http://api_gateway:8000
```

### `PLATFORM_ALERT_INGEST_PATH`

Path appended to `PLATFORM_API_URL` for platform alert ingest.

Default:

```bash
/api/v1/internal/ai-shield/events
```

### `PLATFORM_ALERT_INGEST_TIMEOUT_SECONDS`

HTTP timeout for the platform ingest call.

### `OPENAI_API_KEY`

Optional but required if you want the gateway to make live OpenAI requests in the standalone local path.

### `ANTHROPIC_API_KEY`

Optional Anthropic provider key for local standalone forwarding.

### `LOG_LEVEL`

Service log verbosity.

Typical values:

- `DEBUG`
- `INFO`
- `WARN`
- `ERROR`

## Gateway Variables

### `SERVICES_URL`

Base URL of the services API used for guardrails and internal key lookup.

Compose default:

```bash
http://services:8000
```

### `INTERNAL_SERVICE_TOKEN`

Must match the services value.

### `TELEMETRY_MODE`

Controls telemetry sink behavior.

Current common values:

- `stdout`
- `http`

Use `http` for the normal standalone flow.
`stdout` is only for local debug output and bypasses services event storage plus SIEM export.

### `OPENAI_BASE_URL`

Optional override for OpenAI-compatible upstream endpoints.

Default:

```bash
https://api.openai.com/v1
```

### `PORT`

Gateway listen port. The container default remains `8080`.

## Request Headers

The current chat/completions handlers expect:

- `X-Tenant-ID`
- `X-Realm`
- optional `X-App-ID`

If you omit `X-Tenant-ID` or `X-Realm`, the gateway returns `400`.

## Minimal Local `.env`

```bash
POSTGRES_DB=sentinelgrid_ai_shield
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_URL=postgresql://postgres:postgres@postgres:5432/sentinelgrid_ai_shield
INTERNAL_SERVICE_TOKEN=internal-service-token-change-in-production
OPENAI_API_KEY=sk-your-openai-key
LOG_LEVEL=INFO
TELEMETRY_MODE=http
PLATFORM_ALERT_INGEST_ENABLED=false
```

## Current Runtime Adapter Support

- `splunk_hec`: implemented
- `microsoft_sentinel_dcr`: config contract and docs only
- `ibm_qradar_cef_syslog`: config contract and docs only

## Security Notes

- do not commit `.env`
- use a secret manager or container runtime secret injection in production
- rotate `INTERNAL_SERVICE_TOKEN` before external deployments
- store SIEM credentials in environment variables or a vault, not inline in config files
