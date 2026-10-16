# Examples

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains small working examples for the standalone stack.

## cURL

- `curl/01-health-check.sh`
- `curl/02-create-ai-app.sh`
- `curl/03-chat-completion.sh`
- `curl/04-guardrails.sh`

These are intended to be run after:

```bash
cp .env.example .env
docker compose up --build
```

## Config

- `config/siem-destinations.yaml`
- `config/siem-destination.splunk.yaml`
- `config/siem-destination.sentinel.yaml`
- `config/siem-destination.qradar.yaml`

These demonstrate the standard external-SIEM configuration contract.

Current runtime status:

- Splunk HEC example: live adapter
- Sentinel example: config template for the next adapter
- QRadar example: config template for the next adapter

To enable Splunk in the compose stack:

```bash
cp .env.example .env
```

Add or confirm:

```bash
TELEMETRY_MODE=http
SIEM_EXPORT_ENABLED=true
SIEM_EXPORT_CONFIG_FILE=/app/config/siem-destination.splunk.yaml
SPLUNK_HEC_TOKEN=your-hec-token
```

Then edit `config/siem-destination.splunk.yaml` for your endpoint and restart `services` plus `gateway`.

## Events

- `events/ai-event.blocked.json`

This is a sample normalized event payload for adapter development and mapping.

## Python

- `python/openai_client.py`

This example uses the OpenAI SDK pointed at the local gateway and passes the required tenant headers with `httpx`.

## Node

- `node/openai-client.mjs`

This example uses the official `openai` client and the gateway's OpenAI-compatible API.
