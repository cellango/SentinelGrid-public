ARG SENTINELGRID_API_BASE_IMAGE=sentinelgrid/api-base:latest
FROM ${SENTINELGRID_API_BASE_IMAGE}

USER root

RUN mkdir -p /app/tmp && \
    chown -R sentinelgrid:sentinelgrid /app

# Copy shared libs (relative to backend/)
COPY --chown=sentinelgrid:sentinelgrid libs ./libs

# Copy application code
COPY --chown=sentinelgrid:sentinelgrid services/orchestrator/app ./app

# Set Python path to include both app and libs
ENV PYTHONPATH=/app:/app/libs

USER sentinelgrid

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
