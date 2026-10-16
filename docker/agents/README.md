# SentinelGrid Agent Docker Images

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


Docker images for SentinelGrid agents.

## Available Images

### Endpoint Protection Agent

Based on Wazuh agent, rebranded for SentinelGrid.

**Image:** `sentinelgrid/endpoint-protection-agent:latest`

**Features:**
- Host-based intrusion detection
- File integrity monitoring
- Configuration assessment
- Vulnerability detection
- Log collection

## Usage

### Docker Run

```bash
docker run -d \
  --name sentinelgrid-agent \
  --network host \
  --privileged \
  -e SENTINELGRID_MANAGER_HOST=manager.sentinelgrid.ai \
  -e SENTINELGRID_MANAGER_PORT=1514 \
  -e SENTINELGRID_TENANT_TOKEN=YOUR_TENANT_TOKEN \
  -v /:/host:ro \
  sentinelgrid/endpoint-protection-agent:latest
```

### Docker Compose

```bash
# Set tenant token
export SENTINELGRID_TENANT_TOKEN=your-token-here

# Start agent
docker-compose up -d
```

## Environment Variables

- `SENTINELGRID_MANAGER_HOST` - Manager hostname (default: manager.sentinelgrid.ai)
- `SENTINELGRID_MANAGER_PORT` - Manager port (default: 1514)
- `SENTINELGRID_TENANT_TOKEN` - Tenant authentication token (required)

## Volumes

- `/var/ossec/etc` - Agent configuration
- `/var/ossec/logs` - Agent logs
- `/var/ossec/queue` - Agent queue
- `/host` - Host filesystem (read-only, for monitoring)

## Building

```bash
# Build image
docker build -f Dockerfile.endpoint-protection -t sentinelgrid/endpoint-protection-agent:1.0.0 .

# Tag as latest
docker tag sentinelgrid/endpoint-protection-agent:1.0.0 sentinelgrid/endpoint-protection-agent:latest

# Push to registry
docker push sentinelgrid/endpoint-protection-agent:1.0.0
docker push sentinelgrid/endpoint-protection-agent:latest
```

## Publishing

Images are published to:
- Docker Hub: `sentinelgrid/endpoint-protection-agent`
- GitHub Container Registry: `ghcr.io/sentinelgrid/endpoint-protection-agent`

## Security Considerations

- **Privileged Mode**: Required for file integrity monitoring and network monitoring
- **Host Network**: Required for proper network visibility
- **Read-Only Host Mount**: Host filesystem mounted read-only for safety
- **Capabilities**: Minimal required capabilities (SYS_ADMIN, NET_ADMIN, AUDIT_CONTROL, AUDIT_READ)

## Health Check

The container includes a health check that verifies the agent is active:

```bash
# Check health
docker ps --filter "name=sentinelgrid-agent" --format "{{.Status}}"
```

## Troubleshooting

### View Logs

```bash
docker logs sentinelgrid-agent
```

### Check Agent Status

```bash
docker exec sentinelgrid-agent /var/ossec/bin/agent_control -l
```

### Restart Agent

```bash
docker restart sentinelgrid-agent
```

