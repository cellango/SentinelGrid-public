#
# email_ingestion_service
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, pydantic, etc.)
# Updated: Dec 3, 2025 - Containerization Strategy Rollout
#

FROM sentinelgrid/api-base:latest

# Install service-specific dependencies
USER root
COPY libs/requirements.txt /tmp/libs-requirements.txt
COPY services/email_ingestion_service/requirements.txt /tmp/email-ingestion-requirements.txt
RUN pip install --no-cache-dir -r /tmp/libs-requirements.txt && \
    grep -v "^-r ..\\/..\\/libs\\/requirements.txt" /tmp/email-ingestion-requirements.txt > /tmp/email-requirements-clean.txt && \
    pip install --no-cache-dir -r /tmp/email-requirements-clean.txt && \
    rm /tmp/libs-requirements.txt /tmp/email-ingestion-requirements.txt /tmp/email-requirements-clean.txt
USER sentinelgrid

# Copy shared libs
COPY libs ./libs

# Copy application code
COPY services/email_ingestion_service/app ./app

# Set Python path
ENV PYTHONPATH=/app:/app/libs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
