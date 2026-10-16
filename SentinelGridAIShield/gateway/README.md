# Gateway

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


The gateway is the low-latency edge of `SentinelGridAIShield`.
It accepts OpenAI-compatible requests, runs policy checks, fetches provider keys through the services app, and forwards traffic to the selected provider.

## Features

- OpenAI-compatible chat, completions, and embeddings endpoints
- Header-based tenant and app context
- Launch-supported provider routing for OpenAI
- Explicit rejection of unsupported Anthropic and local provider paths
- Guardrails and telemetry hooks
- Simple local development with `go test` and `go run`

## Build

```bash
go build -o bin/gateway ./cmd/gateway
```

## Run

```bash
export SERVICES_URL="http://localhost:8024"
export INTERNAL_SERVICE_TOKEN="internal-service-token-change-in-production"
go run ./cmd/gateway
```

If you run the services process directly with `uvicorn` on port `8000`, point `SERVICES_URL` at `http://localhost:8000` instead.

## Launch-Supported Providers

- `openai` is the only launch-supported provider family
- `anthropic` and `local` remain compiled into the codebase for future work, but the gateway rejects those model families instead of returning mock responses
- `/health` reports `supported_providers` and `disabled_providers` so deployment checks can verify the active launch boundary

## Required Environment Variables

- `SERVICES_URL`: services base URL, default `http://localhost:8000` for direct process runs. In the standalone compose flow the externally exposed services port is `8024`.
- `INTERNAL_SERVICE_TOKEN`: token shared with the services app for internal key fetches
- `TELEMETRY_MODE`: `stdout` or `http`
- `LOG_LEVEL`: `debug`, `info`, `warn`, or `error`
- `PORT`: listen port, default `8080`

Use `TELEMETRY_MODE=http` for the normal standalone flow so events reach the services API, appear in `ai_events`, and can be exported to SIEM destinations.
Use `stdout` only for local debug output.

## Request Context

Current handlers expect:

- `X-Tenant-ID`
- `X-Realm`
- optional `X-App-ID`

`X-App-ID` may be a human-readable label or a UUID.
If you want the services DB to populate the `ai_events.ai_app_id` UUID column, pass the AI app UUID returned by the services API.

## Related Docs

- [Root Quickstart](../GETTING_STARTED.md)
- [Architecture](../docs/architecture.md)
- [Gateway Integration](../docs/gateway-integration.md)
