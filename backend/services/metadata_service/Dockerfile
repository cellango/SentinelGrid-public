#
# Metadata Service
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, pydantic, etc.)
# Created: Dec 3, 2025 - Service Consolidation
# Consolidates: cmdb_service + vulnerability_service + incident_service + tenant_service
#

FROM sentinelgrid/api-base:latest

# No unique dependencies - all in base image

# Copy shared libs
COPY libs ./libs

# Copy application code
COPY services/metadata_service/app ./app

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

