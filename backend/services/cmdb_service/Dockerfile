#
# cmdb_service
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, pydantic, etc.)
# Updated: Dec 3, 2025 - Containerization Strategy Rollout
#

FROM sentinelgrid/api-base:latest

# No unique dependencies - all in base image

# Set workdir
WORKDIR /app

# Copy shared libs and app code
COPY libs ./libs
COPY services/cmdb_service/app ./app

# Set Python path to include libs
ENV PYTHONPATH=/app:/app/libs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
