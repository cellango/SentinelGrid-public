# Operations

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This document covers the practical runtime behavior of the standalone package.

## Health Endpoints

- gateway: `GET /health`
- services: `GET /health`

## Useful Service Endpoints

- `POST /api/v1/ai-apps/`
- `POST /api/v1/ai-policies/`
- `GET /api/v1/ai-events/`
- `POST /api/v1/guardrails/scan/pii`
- `POST /api/v1/guardrails/scan/secrets`
- `POST /api/v1/guardrails/scan/injection`

## External SIEM Delivery Point

The preferred standalone export architecture is:

1. gateway emits normalized telemetry into the services ingestion path
2. services persists event summaries
3. services triggers SIEM export in a background task after the DB commit succeeds

Current runtime support:

- Splunk HEC: implemented
- Microsoft Sentinel: documented interface, adapter not implemented yet
- IBM QRadar: documented interface, adapter not implemented yet

See [siem-export.md](siem-export.md).

## Common Failure Modes

### Missing Tenant Headers

Symptom:

- gateway returns `400`

Likely cause:

- `X-Tenant-ID` or `X-Realm` was not provided

### Provider Error

Symptom:

- gateway returns `500`
- response error type is `provider_error`

Likely causes:

- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is not configured
- upstream provider rejected the request
- the gateway could not fetch the internal key from services

### Events Missing From Services

Symptom:

- gateway requests work
- `GET /api/v1/ai-events` stays empty

Likely cause:

- `TELEMETRY_MODE=stdout` instead of `http`

### SIEM Export Warning Logs

Symptom:

- services logs show SIEM export warnings after telemetry ingestion

Likely causes:

- `SIEM_EXPORT_ENABLED=true` but `SIEM_EXPORT_CONFIG_FILE` does not exist in the container
- `SPLUNK_HEC_TOKEN` is missing from the services environment
- the Splunk HEC endpoint, token, index, or sourcetype is wrong
- a non-Splunk destination was enabled before its adapter exists

### Service Test Failures

Symptom:

- `pytest` fails before tests run

Likely cause:

- `TEST_DATABASE_URL` points to PostgreSQL, but PostgreSQL is not running or not reachable

## Suggested Bring-Up Sequence

1. verify `.env`
2. start `docker compose up --build`
3. check both `/health` endpoints
4. create an AI app record
5. send a chat request with tenant headers
6. query events

## Logs

Compose logs:

```bash
docker compose logs -f gateway
docker compose logs -f services
docker compose logs -f postgres
```

When Splunk export is enabled, the services logs are the authoritative place to confirm delivery success or failure.

## Smoke Test Commands

The simplest smoke path is:

```bash
./tests/integration_test.sh
```

For a broader pass:

```bash
./tests/run_all_tests.sh
```
