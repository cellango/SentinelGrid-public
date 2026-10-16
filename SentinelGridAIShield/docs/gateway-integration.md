# Gateway Integration

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


The gateway exposes OpenAI-compatible endpoints at `http://localhost:8023/v1`.

## Required Headers

Current handlers expect:

- `X-Tenant-ID`
- `X-Realm`
- optional `X-App-ID`

## cURL Example

```bash
curl -X POST http://localhost:8023/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-Realm: demo" \
  -H "X-App-ID: demo-app" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Explain prompt injection in one paragraph."}
    ]
  }'
```

## Python Example

```python
from openai import OpenAI
import httpx

client = OpenAI(
    base_url="http://localhost:8023/v1",
    api_key="not-used-by-this-local-dev-path",
    http_client=httpx.Client(
        headers={
            "X-Tenant-ID": "11111111-1111-1111-1111-111111111111",
            "X-Realm": "demo",
            "X-App-ID": "demo-app",
        }
    ),
)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello from the gateway"}],
)

print(response.choices[0].message.content)
```

## Examples Directory

This repository also includes runnable examples:

- `examples/curl/01-health-check.sh`
- `examples/curl/02-create-ai-app.sh`
- `examples/curl/03-chat-completion.sh`
- `examples/curl/04-guardrails.sh`
- `examples/python/openai_client.py`
- `examples/node/openai-client.mjs`

## Local Provider Keys

For the standalone stack, the services app reads provider keys from environment variables such as:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

The gateway fetches those keys through the internal services endpoint before making the upstream request.

## Failure Modes

- missing `X-Tenant-ID` or `X-Realm`: `400`
- policy violation: `403`
- no provider key configured or upstream request failed: `500`
