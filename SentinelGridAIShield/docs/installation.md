# Installation

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This document covers the recommended installation and configuration flow for `SentinelGridAIShield`.

## Prerequisites

- Docker Compose
- a reachable PostgreSQL port if you are not using the bundled compose stack
- an upstream provider key such as `OPENAI_API_KEY` if you want real model responses

## Recommended Path: Docker Compose

### 1. Create Local Configuration

```bash
cp .env.example .env
```

At minimum set:

```bash
OPENAI_API_KEY=sk-your-openai-key
INTERNAL_SERVICE_TOKEN=internal-service-token-change-in-production
TELEMETRY_MODE=http
```

### 2. Start The Stack

```bash
docker compose up --build
```

The compose stack includes:

- `postgres`
- `services`
- `gateway`

The services container mounts [../examples/config](../examples/config) at `/app/config`, so SIEM destination files are available inside the container without rebuilding the image.

### 3. Verify Health

```bash
curl http://localhost:8023/health
curl http://localhost:8024/health
```

### 4. Register An App

```bash
curl -X POST http://localhost:8024/api/v1/ai-apps/ \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "11111111-1111-1111-1111-111111111111",
    "name": "demo-app",
    "environment": "dev",
    "allowed_models": ["gpt-4o-mini"]
  }'
```

### 5. Test The Gateway

```bash
curl -X POST http://localhost:8023/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-Realm: demo" \
  -H "X-App-ID: demo-app" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello from SentinelGridAIShield"}]
  }'
```

If you want the `ai_events.ai_app_id` column populated in PostgreSQL, replace `X-App-ID: demo-app` with the AI app UUID returned by the app-registration response.

## Alternative Path: Run Services Individually

### Services

```bash
cd services
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Required environment variables:

- `DB_URL`
- `INTERNAL_SERVICE_TOKEN`
- `TELEMETRY_MODE=http` in the gateway if you want event storage and SIEM export
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` if you want local upstream access through the gateway

### Gateway

```bash
cd gateway
go run ./cmd/gateway
```

Required environment variables:

- `SERVICES_URL`
- `INTERNAL_SERVICE_TOKEN`
- `TELEMETRY_MODE`

If you want Splunk export in the direct-process path, also set:

- `SIEM_EXPORT_ENABLED=true`
- `SIEM_EXPORT_CONFIG_FILE=../examples/config/siem-destination.splunk.yaml`
- `SPLUNK_HEC_TOKEN=<your-token>`

## Optional: Enable Splunk HEC Export

1. Set `SIEM_EXPORT_ENABLED=true` in `.env`.
2. Point `SIEM_EXPORT_CONFIG_FILE` at `/app/config/siem-destination.splunk.yaml` in compose, or a local path if you run services directly.
3. Set `SPLUNK_HEC_TOKEN`.
4. Edit [siem-destination.splunk.yaml](../examples/config/siem-destination.splunk.yaml) for your Splunk HEC endpoint and routing values.
5. Restart `services` and `gateway`.

The current runtime supports Splunk HEC only. Sentinel and QRadar examples remain disabled templates for the shared interface.

## Expected First-Run Flow

1. start PostgreSQL
2. start the services app
3. start the gateway
4. register an app
5. send a test request with tenant headers
6. inspect events from the services API

## Verification Checklist

- gateway `/health` returns `200`
- services `/health` returns `200`
- app registration succeeds
- gateway returns either a completion or a clear provider error if upstream keys are missing
- event query returns data for the test tenant
- if Splunk export is enabled, the services logs do not show HEC delivery warnings
