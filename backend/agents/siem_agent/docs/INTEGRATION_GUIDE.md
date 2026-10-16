# SIEM Agent Integration Guide

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


This guide describes how other SentinelGrid services integrate with the SIEM Agent.

## Overview

The SIEM Agent provides APIs for:
- **Alert Management**: Creating, retrieving, updating alerts
- **Log Search**: Searching events and logs
- **Entity Timelines**: Getting event timelines for users, IPs, hosts, etc.
- **Statistics**: Aggregated metrics and counts

## Authentication

### User-Facing APIs
User-facing APIs require JWT tokens from Keycloak. The `tenant_id` is extracted from the token.

### Internal APIs
Internal APIs use service-to-service authentication with a shared token. Include:
- `Authorization: Bearer <internal-service-token>`
- `X-Tenant-ID: <tenant-uuid>`

**⚠️ Security Note**: In production, use mTLS or service mesh authentication instead of shared tokens.

## Integration Patterns

### 1. SOC Agent Integration

SOC Agent uses SIEM Agent for:
- Creating alerts from detection rules
- Enriching alerts with related events
- Searching events for investigation

#### Creating Alerts

```python
import httpx

async def create_alert(tenant_id: str, alert_data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://siem_agent:8000/internal/siem/alerts/create",
            json=alert_data,
            headers={
                "Authorization": "Bearer <internal-token>",
                "X-Tenant-ID": tenant_id
            }
        )
        return response.json()
```

#### Enriching Alerts with Events

```python
async def enrich_alert(tenant_id: str, alert_id: str, event_ids: list):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://siem_agent:8000/internal/siem/alerts/{alert_id}/events",
            json=event_ids,
            headers={
                "Authorization": "Bearer <internal-token>",
                "X-Tenant-ID": tenant_id
            }
        )
        return response.json()
```

#### Searching Events

```python
async def search_events(tenant_id: str, query: str, start_time: str = None):
    params = {"query": query, "limit": 100}
    if start_time:
        params["start_time"] = start_time
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://siem_agent:8000/internal/siem/search/events",
            params=params,
            headers={
                "Authorization": "Bearer <internal-token>",
                "X-Tenant-ID": tenant_id
            }
        )
        return response.json()
```

### 2. IAM Agent Integration

IAM Agent uses SIEM Agent for:
- Querying user activity timelines
- Checking IP address activity
- Validating user behavior patterns

#### Getting User Timeline

```python
async def get_user_timeline(tenant_id: str, user_id: str, start_time: str = None):
    params = {
        "entity_type": "user",
        "entity_id": user_id,
        "limit": 1000
    }
    if start_time:
        params["start_time"] = start_time
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://siem_agent:8000/internal/siem/timeline/entity",
            params=params,
            headers={
                "Authorization": "Bearer <internal-token>",
                "X-Tenant-ID": tenant_id
            }
        )
        return response.json()
```

#### Getting IP Timeline

```python
async def get_ip_timeline(tenant_id: str, ip_address: str):
    params = {
        "entity_type": "ip",
        "entity_id": ip_address,
        "limit": 1000
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://siem_agent:8000/internal/siem/timeline/entity",
            params=params,
            headers={
                "Authorization": "Bearer <internal-token>",
                "X-Tenant-ID": tenant_id
            }
        )
        return response.json()
```

### 3. SOAR Agent Integration

SOAR Agent uses SIEM Agent for:
- Getting observable types for playbooks
- Extracting observables from alerts
- Enriching incidents with SIEM data

#### Getting Observable Types

```python
async def get_observable_types():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://siem_agent:8000/siem/observables/types"
        )
        return response.json()
```

#### Extracting Observables from Alert

```python
def extract_observables(alert: dict) -> list:
    """Extract observables from an alert."""
    observables = []
    
    # Extract IP address
    if alert.get("source_ip"):
        observables.append({
            "type": "ip",
            "value": alert["source_ip"]
        })
    
    # Extract user ID
    if alert.get("user_id"):
        observables.append({
            "type": "user",
            "value": alert["user_id"]
        })
    
    # Extract hash from description (example)
    import re
    hash_match = re.search(r'[a-f0-9]{32}', alert.get("description", ""))
    if hash_match:
        observables.append({
            "type": "hash_md5",
            "value": hash_match.group()
        })
    
    return observables
```

## Error Handling

All APIs return standard HTTP status codes:
- `200 OK`: Success
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Example error response:
```json
{
    "detail": "Alert not found"
}
```

## Rate Limiting

Internal APIs have rate limiting applied. If you exceed limits, you'll receive:
- HTTP 429 Too Many Requests
- `Retry-After` header indicating when to retry

## Best Practices

1. **Always include tenant_id**: Even with internal APIs, always provide `X-Tenant-ID` header
2. **Handle errors gracefully**: Check response status codes and handle errors appropriately
3. **Use async/await**: Use async HTTP clients for better performance
4. **Cache when possible**: Cache observable types and other static data
5. **Retry with backoff**: Implement exponential backoff for transient errors

## Testing

See `tests/test_integration.py` for integration test examples.

## Support

For issues or questions, contact the SentinelGrid platform team.

