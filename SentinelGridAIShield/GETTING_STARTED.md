# Getting Started

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


## Prerequisites

- Docker Desktop or Docker Engine with Compose
- An OpenAI API key if you want live upstream completions

## 1. Configure Local Environment

```bash
cp .env.example .env
```

Set at least:

```bash
OPENAI_API_KEY=sk-your-openai-key
INTERNAL_SERVICE_TOKEN=internal-service-token-change-in-production
TELEMETRY_MODE=http
```

## 2. Start The Stack

```bash
docker compose up --build
```

This starts:

- PostgreSQL on `localhost:5432`
- Services API on `localhost:8024`
- Gateway on `localhost:8023`

## 3. Verify Health

```bash
curl http://localhost:8023/health
curl http://localhost:8024/health
```

Expected response:

```json
{"status":"healthy"}
```

## 4. Create An App Record

The services layer stores app metadata and policies. Use a UUID org ID.

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

## 5. Send A Request Through The Gateway

```bash
curl -X POST http://localhost:8023/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-Realm: demo" \
  -H "X-App-ID: demo-app" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Summarize why secure AI gateways matter."}
    ]
  }'
```

Notes:

- `X-Tenant-ID` and `X-Realm` are currently required by the gateway handlers.
- For local development, the services app serves provider keys from environment variables such as `OPENAI_API_KEY`.
- If you want `ai_events.ai_app_id` populated in PostgreSQL, set `X-App-ID` to the AI app UUID returned by the services API. Human-readable labels still work for gateway context and SIEM raw payloads.

## 6. Inspect Guardrails And Events

Run direct guardrails scans:

```bash
curl -X POST http://localhost:8024/api/v1/guardrails/scan/pii \
  -H "Content-Type: application/json" \
  -d '{"text":"Contact me at alice@example.com"}'
```

Query events:

```bash
curl "http://localhost:8024/api/v1/ai-events/?org_id=11111111-1111-1111-1111-111111111111&limit=20"
```

## 7. Optional: Enable Splunk HEC Export

The current runtime implements Splunk HEC delivery from the services layer after each telemetry write commits.

Add to `.env`:

```bash
SIEM_EXPORT_ENABLED=true
SIEM_EXPORT_CONFIG_FILE=/app/config/siem-destination.splunk.yaml
SPLUNK_HEC_TOKEN=your-hec-token
```

Then edit [siem-destination.splunk.yaml](examples/config/siem-destination.splunk.yaml) and restart:

```bash
docker compose up -d --build services gateway
```

Microsoft Sentinel and QRadar example files are included for the same interface, but those runtime adapters are not implemented yet.

## Running Tests

Gateway tests:

```bash
make test-gateway
```

Services tests:

```bash
TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/sentinelgrid_ai_shield_test make test-services
```

Full test helper:

```bash
./tests/run_all_tests.sh
```

## Next Docs

- [Architecture](docs/architecture.md)
- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Gateway Integration](docs/gateway-integration.md)
- [Operations](docs/operations.md)
- [Examples](examples/README.md)
- [Testing](tests/README.md)
