# Keycloak Troubleshooting Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Issue: "This site can't be reached" when clicking Sign in

### Problem
When clicking "Sign in" on the website, users get "This site can't be reached" error. This is because Keycloak is not running or not accessible.

### Current Status
- Keycloak container exists but is failing to start
- Error: "Failed to run 'build' command"
- Keycloak should be accessible at `http://localhost:8081`

### Solution Steps

#### 1. Check Keycloak Status
```bash
docker ps -a | grep keycloak
```

#### 2. Check Keycloak Logs
```bash
docker logs sentinelgrid-keycloak-1 --tail 50
```

#### 3. Start Keycloak Services
```bash
cd /path/to/SentinelGrid
docker-compose -f docker-compose.dev.yml up -d keycloak keycloak_db
```

#### 4. Wait for Keycloak to Start
Keycloak can take 30-60 seconds to fully start. Check if it's ready:
```bash
curl http://localhost:8081/health
# or
curl http://localhost:8081/realms/sentinelgrid/.well-known/openid-configuration
```

#### 5. If Keycloak Fails to Start

**Option A: Rebuild Keycloak Container**
```bash
docker-compose -f docker-compose.dev.yml stop keycloak
docker-compose -f docker-compose.dev.yml rm -f keycloak
docker-compose -f docker-compose.dev.yml up -d keycloak keycloak_db
```

**Option B: Check Database Connection**
```bash
# Check if Keycloak DB is running
docker ps | grep keycloak_db

# Check database connection from Keycloak container
docker exec sentinelgrid-keycloak-1 ping keycloak_db
```

**Option C: Try Building Keycloak First**
For Keycloak 26.x, you might need to build first:
```bash
docker exec sentinelgrid-keycloak-1 /opt/keycloak/bin/kc.sh build --db=postgres
docker-compose -f docker-compose.dev.yml restart keycloak
```

#### 6. Verify Keycloak is Accessible
Once Keycloak is running, test the login URL:
```bash
curl "http://localhost:8081/realms/sentinelgrid/protocol/openid-connect/auth?client_id=sentinelgrid-frontend&redirect_uri=http://localhost:3000/auth/callback&response_type=code&scope=openid%20profile%20email"
```

This should return an HTML login page, not an error.

### Configuration

**Keycloak URL**: `http://localhost:8081` (mapped from container port 8080)
**Realm**: `sentinelgrid`
**Client ID**: `sentinelgrid-frontend` (for website) or `sentinelgrid-api` (for backend)

### Environment Variables

The website uses these defaults (can be overridden with `.env`):
- `NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8081`
- `NEXT_PUBLIC_KEYCLOAK_REALM=sentinelgrid`
- `NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=sentinelgrid-frontend`

### Common Issues

1. **Keycloak not running**: Start with `docker-compose up -d keycloak`
2. **Wrong port**: Keycloak is on port 8081 (not 8080)
3. **Database not ready**: Wait for `keycloak_db` to be healthy before starting Keycloak
4. **Realm not imported**: Check if `./infra/keycloak/realm-export.json` exists
5. **Client not configured**: Ensure `sentinelgrid-frontend` client exists in the realm

### Quick Fix

If Keycloak keeps failing, try this sequence:
```bash
# Stop everything
docker-compose -f docker-compose.dev.yml stop keycloak keycloak_db

# Remove Keycloak container (keeps DB data)
docker-compose -f docker-compose.dev.yml rm -f keycloak

# Start fresh
docker-compose -f docker-compose.dev.yml up -d keycloak_db
sleep 5
docker-compose -f docker-compose.dev.yml up -d keycloak

# Wait and check
sleep 30
curl http://localhost:8081/health
```

