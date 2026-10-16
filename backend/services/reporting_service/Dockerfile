#
# reporting_service
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, pydantic, etc.)
# Updated: Dec 3, 2025 - Containerization Strategy Rollout
#

FROM sentinelgrid/api-base:latest

# Install system deps for PDF generation (WeasyPrint)
USER root
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Ensure report storage dir exists and is writable
RUN mkdir -p /tmp/reports && chown -R sentinelgrid:sentinelgrid /tmp/reports
USER sentinelgrid

# Copy shared libs first so requirements can include shared constraints
COPY libs ./libs

# Install service-specific dependencies
COPY services/reporting_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY services/reporting_service/app ./app

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
