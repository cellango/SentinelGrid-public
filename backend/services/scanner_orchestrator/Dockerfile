#
# Scanner Orchestrator
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, pydantic, etc.)
#

FROM sentinelgrid/api-base:latest

# Workdir for app
WORKDIR /app

# Install service-specific dependencies
COPY services/scanner_orchestrator/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy shared libs
COPY libs ./libs

# Copy migrations
COPY services/scanner_orchestrator/db ./db

# Copy application code
COPY services/scanner_orchestrator/app ./app

# Set Python path
ENV PYTHONPATH=/app:/app/libs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
