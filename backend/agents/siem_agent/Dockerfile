#
# SIEM Agent Service
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, PyJWT, redis, etc.)
# Updated: Dec 3, 2025 - Containerization Strategy Rollout
#

ARG SENTINELGRID_API_BASE_IMAGE=sentinelgrid/api-base:latest
FROM ${SENTINELGRID_API_BASE_IMAGE}

USER root

# Install service-specific dependencies (only OpenSearch client)
COPY agents/siem_agent/requirements-specific.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy shared libs (relative to backend/)
COPY --chown=sentinelgrid:sentinelgrid libs ./libs

# Copy application code and scripts
COPY --chown=sentinelgrid:sentinelgrid agents/siem_agent/app ./app
COPY --chown=sentinelgrid:sentinelgrid agents/siem_agent/scripts ./scripts
COPY --chmod=755 agents/siem_agent/scripts/wait_for_dependencies.sh /wait_for_dependencies.sh

RUN mkdir -p /app/tmp && \
    chown -R sentinelgrid:sentinelgrid /app

# Set Python path
ENV PYTHONPATH=/app:/libs

USER sentinelgrid

# Expose port
EXPOSE 8000

# Run application with dependency wait
ENTRYPOINT ["/wait_for_dependencies.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
