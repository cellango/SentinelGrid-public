#
# IAM Agent Service
# Uses: sentinelgrid/api-ml (includes api-base + shared ML runtime dependencies)
# Updated: Dec 3, 2025 - Containerization Strategy Phase 2 POC
#

ARG SENTINELGRID_API_ML_IMAGE=sentinelgrid/api-ml:latest
FROM ${SENTINELGRID_API_ML_IMAGE}

USER root

# Git-backed provider and scanning flows still need the git CLI at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Install service-specific dependencies
# Common deps (FastAPI, SQLAlchemy, httpx) and shared ML deps are already in base.
COPY agents/iam_agent/requirements-specific.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy shared libs (relative to backend/)
COPY --chown=sentinelgrid:sentinelgrid libs ./libs

# Copy app code
COPY --chown=sentinelgrid:sentinelgrid agents/iam_agent/app ./app

RUN mkdir -p /app/tmp && \
    chown -R sentinelgrid:sentinelgrid /app

USER sentinelgrid

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
