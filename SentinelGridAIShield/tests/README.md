# Testing

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


`SentinelGridAIShield` ships with three testing layers:

- Go unit tests for the gateway
- Python API tests for the services app
- integration and end-to-end scripts for the full local stack

## Prerequisites

- Go 1.22+
- Python 3.11+
- PostgreSQL for service tests
- Docker Compose for full-stack integration

## Gateway Unit Tests

```bash
make test-gateway
```

This runs:

```bash
cd gateway && go test -v ./...
```

## Services Tests

Service tests assume PostgreSQL because the models use PostgreSQL UUID and ARRAY types.

```bash
TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/sentinelgrid_ai_shield_test \
make test-services
```

Targeted SIEM exporter unit tests do not require PostgreSQL:

```bash
cd services
pytest tests/test_siem_export.py
```

## Full Test Helper

```bash
./tests/run_all_tests.sh
```

The helper runs:

1. gateway unit tests
2. services tests
3. integration checks against a running local stack
4. end-to-end smoke checks

## Start The Local Stack For Integration

```bash
docker compose up --build
```

Then run:

```bash
./tests/integration_test.sh
python3 ./tests/e2e_test.py
```

## CI

The split-ready subtree includes a GitHub Actions workflow at `.github/workflows/ci.yml` that runs:

- gateway unit tests
- services tests against a PostgreSQL service container

## Notes

- integration and e2e scripts are designed for local verification, not fast CI
- the gateway can make live upstream requests only when a provider key such as `OPENAI_API_KEY` is configured in `.env`
- the documented standalone path expects `TELEMETRY_MODE=http`; `stdout` skips services-side event storage and SIEM export
