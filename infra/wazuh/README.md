# SentinelGrid Endpoint Manager Configuration

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


**Component:** SentinelGrid Endpoint Manager (Wazuh Manager 4.8.0)  
**Purpose:** Central management server for SentinelGrid Endpoint Protection agents

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `filebeat.yml` | Filebeat configuration for routing events to tenant-specific OpenSearch indices |
| `ossec.conf` | Wazuh Manager main configuration |
| `opensearch-index-template.json` | OpenSearch index template for Wazuh alert data |
| `README.md` | This file |

---

## Architecture

```
Endpoint Agents (Customer Infrastructure)
    ↓ TCP 1514 (TLS)
Wazuh Manager (SentinelGrid Endpoint Manager)
    ├─ Receives events from agents
    ├─ Stores agent labels (tenant_id)
    ├─ Enriches events with labels
    └─ Processes security rules
    ↓ Filebeat
OpenSearch (SentinelGrid SIEM)
    └─ Stores in tenant-specific indices
        wazuh-alerts-{tenant_id}-YYYY.MM.DD
```

---

## Key Configuration Points

### 1. filebeat.yml

**Purpose:** Routes Wazuh events to tenant-specific OpenSearch indices

**Critical Features:**
- Extracts `tenant_id` from `agent.labels.tenant_id`
- Routes to dynamic index: `wazuh-alerts-{tenant_id}-YYYY.MM.DD`
- Drops events without tenant_id (safety check)
- Copies tenant_id to top level for easier queries

**Multi-Tenancy:**
```yaml
# This processor copies tenant_id from agent labels
processors:
  - copy_fields:
      fields:
        - from: agent.labels.tenant_id
          to: tenant_id
  
  # Safety: drop events without tenant_id
  - drop_event:
      when:
        not:
          has_fields: ['agent.labels.tenant_id']

# Dynamic routing by tenant_id
output.elasticsearch:
  indices:
    - index: "wazuh-alerts-%{[agent.labels.tenant_id]}-%{+yyyy.MM.dd}"
```

### 2. ossec.conf

**Purpose:** Wazuh Manager main configuration

**Configured Modules:**
- File Integrity Monitoring (FIM)
- Rootcheck (policy compliance)
- Vulnerability Detection
- Syscollector (system inventory)
- Security Configuration Assessment (SCA)

**Agent Communication:**
- Port 1514/TCP - Agent data communication
- Port 1515/TCP - Agent enrollment
- Protocol: TCP with optional TLS

### 3. opensearch-index-template.json

**Purpose:** Define mapping for Wazuh alert indices

**Key Mappings:**
- `tenant_id` - Keyword for filtering
- `agent.labels.tenant_id` - Keyword (critical for isolation)
- `rule.level` - Integer (0-15 severity)
- `rule.mitre.*` - MITRE ATT&CK mapping
- Compliance fields (PCI-DSS, GDPR, NIST, HIPAA)

---

## How tenant_id Labeling Works

### Agent Registration Flow

1. **User calls API** with JWT (contains tenant_id)
   ```
   POST /api/v1/wazuh/agents/register
   Authorization: Bearer eyJhbGc...
   ```

2. **Service extracts tenant_id** from JWT
   ```
   tenant_id = "123e4567-e89b-12d3-a456-426614174000"
   ```

3. **Agent created in Wazuh Manager**
   ```
   POST /agents {"name": "web-server-01"}
   Response: {"id": "001"}
   ```

4. **Label set on agent (server-side)**
   ```
   PUT /agents/001/labels
   {
     "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
     "registered_via": "sentinelgrid_api"
   }
   ```

5. **Agent sends events** (no tenant_id in agent)
   ```
   Agent → Manager: <event data>
   ```

6. **Manager enriches events** with labels
   ```
   {
     "agent": {
       "id": "001",
       "labels": {
         "tenant_id": "123e4567-e89b-12d3-a456-426614174000"
       }
     },
     "rule": {...},
     "data": {...}
   }
   ```

7. **Filebeat routes to tenant index**
   ```
   Index: wazuh-alerts-123e4567-e89b-12d3-a456-426614174000-2025.12.03
   ```

### Result: Perfect Isolation

- ✅ Each tenant's events in separate indices
- ✅ Agent binary unchanged (no client-side tenant_id)
- ✅ No way for agent to forge tenant_id
- ✅ Queries automatically isolated by index pattern

---

## Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 1514 | TCP | Agent communication (secure) |
| 1515 | TCP | Agent enrollment/registration |
| 55000 | TCP | Wazuh API (REST) |
| 1516 | TCP | Cluster communication (if HA enabled) |

---

## Maintenance

### Update Filebeat Configuration

```bash
# Edit filebeat.yml
vi infra/wazuh/filebeat.yml

# Restart Wazuh Manager (includes Filebeat)
docker-compose restart wazuh-manager
```

### Update Wazuh Configuration

```bash
# Edit ossec.conf
vi infra/wazuh/ossec.conf

# Restart Wazuh Manager
docker-compose restart wazuh-manager
```

### View Wazuh Logs

```bash
# Manager logs
docker-compose exec wazuh-manager tail -f /var/ossec/logs/ossec.log

# API logs
docker-compose exec wazuh-manager tail -f /var/ossec/logs/api.log

# Filebeat logs
docker-compose exec wazuh-manager tail -f /var/log/filebeat/filebeat.log
```

---

## Troubleshooting

### Agents Not Connecting

**Check:**
1. Port 1514 is accessible from agent
2. Agent has correct manager address
3. Agent key is imported correctly
4. Wazuh Manager is running

**Logs:**
```bash
# On agent
sudo tail -f /var/ossec/logs/ossec.log

# On manager
docker-compose logs wazuh-manager | grep "New connection"
```

### Events Not in OpenSearch

**Check:**
1. Filebeat is running
2. Agent has tenant_id label
3. OpenSearch is accessible
4. Index template exists

**Verify:**
```bash
# Check Filebeat status
docker-compose exec wazuh-manager service filebeat status

# Check if indices are being created
curl http://localhost:9200/_cat/indices/wazuh-alerts-*

# Check Filebeat logs for errors
docker-compose exec wazuh-manager tail -f /var/log/filebeat/filebeat.log
```

### Missing tenant_id Labels

**Verify agent labels:**
```bash
# Get Wazuh API token
TOKEN=$(curl -s -u wazuh-api:MyS3cr3tP455w0rd! \
  -X POST http://localhost:55000/security/user/authenticate | jq -r '.data.token')

# Check agent labels
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:55000/agents/001 | jq '.data.labels'

# Expected output:
# {
#   "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
#   "registered_via": "sentinelgrid_api",
#   "platform": "linux"
# }
```

---

## Security Considerations

### Production Deployment

For production, enable:

1. **TLS for agent communication**
   - Generate certificates
   - Configure in `ossec.conf`
   - Update agent installation to use TLS

2. **API authentication**
   - Change default API password
   - Use strong passwords
   - Rotate credentials regularly

3. **Firewall rules**
   - Restrict port 55000 to internal network only
   - Allow ports 1514-1515 from customer networks

4. **High Availability**
   - Run multiple Wazuh Manager nodes
   - Configure cluster mode in `ossec.conf`
   - Use load balancer for `manager.sentinelgrid.ai`

---

## Performance Tuning

### For High Agent Counts (>1000 agents)

**ossec.conf adjustments:**
```xml
<remote>
  <queue_size>262144</queue_size>  <!-- Double the default -->
</remote>
```

**Filebeat adjustments:**
```yaml
output.elasticsearch:
  bulk_max_size: 1000
  worker: 2
```

### For High Event Rates

- Increase Wazuh Manager resources (CPU/RAM)
- Scale Filebeat workers
- Tune OpenSearch shard count
- Enable event archiving selectively

---

## References

- [Wazuh Documentation](https://documentation.wazuh.com/)
- [Filebeat Wazuh Module](https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-module-wazuh.html)
- [OpenSearch Index Templates](https://opensearch.org/docs/latest/im-plugin/index-templates/)

---

**Last Updated:** December 3, 2025  
**Component:** SentinelGrid Endpoint Manager  
**Powered By:** Wazuh 4.8.0

