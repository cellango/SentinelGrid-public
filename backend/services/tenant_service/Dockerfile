#
# Tenant Service
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, pydantic, etc.)
# Updated: Dec 3, 2025 - Containerization Strategy Rollout
#

FROM sentinelgrid/api-base:latest

# Install service-specific dependencies
USER root
COPY services/tenant_service/requirements.txt /tmp/tenant_service.requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-cache-dir -r /tmp/tenant_service.requirements.txt && \
    rm /tmp/tenant_service.requirements.txt
USER sentinelgrid

# Copy shared libs
COPY libs ./libs

# Copy IAM agent shared services (used by enhanced provisioning)
COPY agents/iam_agent/app ./agents/iam_agent/app

# Copy application code
COPY services/tenant_service/app ./app

# Set Python path
ENV PYTHONPATH=/app/agents/iam_agent/app:/app/agents/iam_agent:/app

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
