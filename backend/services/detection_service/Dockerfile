#
# Detection Service
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, pydantic, etc.)
# Updated: Dec 3, 2025 - Containerization Strategy Rollout
#

FROM sentinelgrid/api-base:latest

# Install service-specific dependencies (scheduler, etc.)
COPY services/detection_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy shared libs
COPY libs ./libs

# Copy application code
COPY services/detection_service/app ./app

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
