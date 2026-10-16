#
# API Gateway Service
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, etc.)
# Updated: Dec 3, 2025 - Containerization Strategy Phase 2 POC
#

ARG SENTINELGRID_API_BASE_IMAGE=sentinelgrid/api-base:latest
FROM ${SENTINELGRID_API_BASE_IMAGE}

USER root

# Note: All dependencies already in base image!
# api_gateway has no unique dependencies

# Copy shared libs (relative to backend/)
COPY --chown=sentinelgrid:sentinelgrid libs ./libs

# Copy app code
COPY --chown=sentinelgrid:sentinelgrid services/api_gateway/app ./app

RUN mkdir -p /app/tmp && \
    chown -R sentinelgrid:sentinelgrid /app

USER sentinelgrid

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
