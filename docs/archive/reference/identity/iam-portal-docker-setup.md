# IAM Portal Docker Setup

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Architecture Overview

The IAM Portal is split across two services:

### Backend (IAM Agent Service)
- **Location**: `backend/services/iam_agent/`
- **Docker Service**: `iam_agent` in docker-compose
- **APIs**: 
  - `/api/iam-portal/*` - IAM portal endpoints
  - `/api/iam-portal/policies/*` - Policy endpoints
- **Port**: 8000 (internal)

### Frontend (Main Frontend Service)
- **Location**: `frontend/src/app/dashboard/iam/`
- **Docker Service**: `frontend` in docker-compose
- **Pages**:
  - `/dashboard/iam/people` - People page
  - `/dashboard/iam/my-access` - My Access page
  - `/dashboard/iam/apps` - Apps & Profiles page
  - `/dashboard/iam/policies` - Policies page
- **Port**: 3000 (exposed via nginx)

## Current Docker Setup

### IAM Agent Service

Already configured in `docker-compose.dev.yml`:

```yaml
iam_agent:
  build:
    context: ./backend
    dockerfile: services/iam_agent/Dockerfile
  environment:
    - KEYCLOAK_URL=http://keycloak:8080
    - KEYCLOAK_REALM=sentinelgrid
    - KEYCLOAK_CLIENT_ID=sentinelgrid-iam-agent
    - KEYCLOAK_CLIENT_SECRET=${IAM_AGENT_CLIENT_SECRET}
    - DB_URL=postgresql://sg:sg@postgres:5432/sg
  volumes:
    - ./backend/services/iam_agent/app:/app/app  # Hot reload
  ports:
    - "8000:8000"
  depends_on:
    - postgres
    - keycloak
```

### Frontend Service

Already configured in `docker-compose.dev.yml`:

```yaml
frontend:
  build: ./frontend
  environment:
    - NEXT_PUBLIC_API_BASE=http://localhost:8080
    - NEXT_PUBLIC_IAM_AGENT_URL=http://iam_agent:8000  # Internal
  expose:
    - "3000"
  depends_on:
    - iam_agent
```

## Running with Docker

### Start All Services

```bash
# Start all services including IAM portal
docker-compose -f docker-compose.dev.yml up -d

# Or start specific services
docker-compose -f docker-compose.dev.yml up -d postgres keycloak iam_agent frontend nginx
```

### Check Services

```bash
# Check IAM agent is running
docker-compose -f docker-compose.dev.yml ps iam_agent

# Check frontend is running
docker-compose -f docker-compose.dev.yml ps frontend

# View IAM agent logs
docker-compose -f docker-compose.dev.yml logs -f iam_agent

# View frontend logs
docker-compose -f docker-compose.dev.yml logs -f frontend
```

### Access the UI

1. **Via Nginx** (recommended): `https://localhost:8443` or `http://localhost:8080`
2. **Direct Frontend**: `http://localhost:3000` (if port is exposed)
3. **IAM Agent API**: `http://localhost:8000` (if port is exposed)

## Environment Variables

### IAM Agent Environment Variables

Required in `docker-compose.dev.yml`:

```yaml
iam_agent:
  environment:
    # Keycloak
    - KEYCLOAK_URL=http://keycloak:8080
    - KEYCLOAK_REALM=sentinelgrid
    - KEYCLOAK_CLIENT_ID=sentinelgrid-iam-agent
    - KEYCLOAK_CLIENT_SECRET=${IAM_AGENT_CLIENT_SECRET}
    
    # Database
    - DB_URL=postgresql://sg:sg@postgres:5432/sg
    
    # Optional
    - REDIS_URL=redis://redis:6379
    - MODEL_GATEWAY_URL=http://model_gateway:8000
```

### Frontend Environment Variables

Required in `docker-compose.dev.yml`:

```yaml
frontend:
  environment:
    # IAM Agent URL (internal Docker network)
    - NEXT_PUBLIC_IAM_AGENT_URL=http://iam_agent:8000
    
    # API Gateway
    - NEXT_PUBLIC_API_BASE=http://api_gateway:8000
```

**Important**: The frontend uses `NEXT_PUBLIC_IAM_AGENT_URL` to call IAM portal APIs. This should point to the IAM agent service on the Docker network.

## Nginx Configuration

The frontend is typically served through nginx. Ensure nginx is configured to:

1. **Proxy IAM Portal API calls** to IAM agent:
   ```nginx
   location /api/iam-portal/ {
       proxy_pass http://iam_agent:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

2. **Serve frontend pages**:
   ```nginx
   location / {
       proxy_pass http://frontend:3000;
   }
   ```

## Development vs Production

### Development (Current Setup)

- **Hot Reload**: IAM agent code is mounted as volume for hot reload
- **Direct Access**: Services can be accessed directly on their ports
- **Debugging**: Logs are visible via `docker-compose logs`

### Production

For production, you'll want:

1. **Multi-stage builds** (already in Dockerfiles)
2. **No volume mounts** (use built images)
3. **Environment-specific configs**
4. **Health checks**
5. **Resource limits**

## Testing in Docker

### 1. Start Services

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Wait for Services to be Ready

```bash
# Wait for IAM agent
until curl -f http://localhost:8000/health; do
  echo "Waiting for IAM agent..."
  sleep 2
done

# Wait for frontend
until curl -f http://localhost:3000; do
  echo "Waiting for frontend..."
  sleep 2
done
```

### 3. Run Database Migrations

```bash
# Connect to postgres container
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg

# Run migrations
\i /path/to/015_iam_portal_schema.sql
\i /path/to/016_iam_policies_schema.sql
```

Or copy migrations into container:

```bash
# Copy migration files
docker cp backend/migrations/015_iam_portal_schema.sql \
  $(docker-compose ps -q postgres):/tmp/

# Execute
docker-compose -f docker-compose.dev.yml exec postgres \
  psql -U sg -d sg -f /tmp/015_iam_portal_schema.sql
```

### 4. Test API

```bash
# Get token (from Keycloak)
TOKEN="your-jwt-token"

# Test IAM portal API
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/iam-portal/users
```

### 5. Access UI

Open browser: `http://localhost:3000` or `https://localhost:8443`

## Troubleshooting

### IAM Agent Not Starting

```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs iam_agent

# Common issues:
# - Keycloak not ready (wait for keycloak)
# - Database not ready (wait for postgres)
# - Missing environment variables
```

### Frontend Can't Connect to IAM Agent

**Issue**: `NEXT_PUBLIC_IAM_AGENT_URL` is wrong

**Fix**: 
1. Check environment variable in docker-compose
2. For internal Docker network, use: `http://iam_agent:8000`
3. For external access, use: `http://localhost:8000`

### CORS Errors

**Issue**: Frontend can't call IAM agent API

**Fix**: IAM agent already has CORS middleware configured:
```python
# In app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, restrict `allow_origins` to your frontend domain.

### Database Connection Issues

```bash
# Check postgres is running
docker-compose -f docker-compose.dev.yml ps postgres

# Check connection from IAM agent
docker-compose -f docker-compose.dev.yml exec iam_agent \
  python -c "from app.core.database import engine; engine.connect()"
```

## Building Images

### Build IAM Agent

```bash
docker-compose -f docker-compose.dev.yml build iam_agent
```

### Build Frontend

```bash
docker-compose -f docker-compose.dev.yml build frontend
```

### Build All

```bash
docker-compose -f docker-compose.dev.yml build
```

## Production Deployment

### 1. Update Environment Variables

Create `docker-compose.prod.yml`:

```yaml
version: "3.9"

services:
  iam_agent:
    environment:
      - KEYCLOAK_URL=https://keycloak.example.com
      - KEYCLOAK_REALM=sentinelgrid
      - DB_URL=postgresql://user:pass@postgres:5432/sg
    # Remove volume mounts for production
    # volumes:
    #   - ./backend/services/iam_agent/app:/app/app

  frontend:
    environment:
      - NEXT_PUBLIC_IAM_AGENT_URL=https://api.example.com
      - NODE_ENV=production
```

### 2. Use Production Builds

```bash
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## Summary

✅ **IAM Portal is already dockerized!**

- **Backend**: Part of `iam_agent` service (FastAPI)
- **Frontend**: Part of `frontend` service (Next.js)
- **APIs**: Available at `/api/iam-portal/*` on IAM agent
- **UI**: Available at `/dashboard/iam/*` on frontend

Just start the services and access the UI!

