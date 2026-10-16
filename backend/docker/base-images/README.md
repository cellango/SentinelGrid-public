# SentinelGrid Base Images

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


Shared Docker base images for SentinelGrid services.

---

## Quick Start

### Build All Base Images

```bash
cd backend/docker/base-images
./build-all.sh
```

**Time**: 15-20 minutes (first build)  
**Result**: 3 base images ready to use

---

## Available Images

### sentinelgrid/runtime-python:3.11
**Size**: ~300 MB  
**Purpose**: Foundation for all Python services  
**Contains**: Python 3.11 + build tools + system libraries

### sentinelgrid/api-base:latest
**Size**: ~450 MB  
**Purpose**: REST API services  
**Contains**: FastAPI, SQLAlchemy, Pydantic, httpx, etc.  
**Use for**: 23+ API services

### sentinelgrid/api-ml:latest
**Size**: ~1.5 GB  
**Purpose**: AI/ML services  
**Contains**: PyTorch, Transformers, Presidio, etc.  
**Use for**: model_gateway, ai_enrichment_agent, ai_shield_services

---

## Usage in Service Dockerfiles

### Example: API Service

```dockerfile
FROM sentinelgrid/api-base:latest

# Install service-specific dependencies (if any)
COPY requirements-specific.txt .
RUN pip install -r requirements-specific.txt

# Copy code
COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Example: ML Service

```dockerfile
FROM sentinelgrid/api-ml:latest

# Install service-specific ML models (if any)
RUN python -m transformers.cli download bert-base-uncased

# Copy code
COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Building & Testing

```bash
# Build all images
./build-all.sh

# Build specific tier
./build-all.sh runtime
./build-all.sh api
./build-all.sh ml

# Force rebuild without cache
./build-all.sh --no-cache

# Test an image
docker run sentinelgrid/api-base:latest python -c "import fastapi; print(fastapi.__version__)"
```

---

## Updating Dependencies

### Monthly Updates

1. Edit `requirements/*.txt`
2. Rebuild images: `./build-all.sh`
3. Test with pilot service
4. Push to registry: `./push-to-registry.sh`
5. Update service builds

### Security Patches

Automated weekly via CI/CD pipeline.

---

## Versioning

**Tags**:
- `:latest` - Rolling latest (dev)
- `:1.0` - Semantic version (prod)
- `:3.11` - Python version (runtime only)

**Policy**:
- Development uses `:latest`
- Production pins to `:1.0` or `:1.0.2`

---

## Files

```
base-images/
├── Dockerfile.runtime-python    # Tier 1: Python runtime
├── Dockerfile.api-base          # Tier 2: API services
├── Dockerfile.api-ml            # Tier 3: ML services
├── requirements/
│   ├── api-base.txt             # FastAPI stack
│   └── api-ml.txt               # ML libraries
├── build-all.sh                 # Build script
├── push-to-registry.sh          # Push script
└── README.md                    # This file
```

---

## See Also

- [Containerization Strategy](../../../docs/archive/README.md#retired-references) - Full documentation
- `Migration Guide` (historical reference unavailable) - How to migrate services

