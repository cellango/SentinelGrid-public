#
# mcp_server
# Uses: sentinelgrid/api-base (includes FastAPI, SQLAlchemy, httpx, pydantic, etc.)
# Updated: Dec 3, 2025 - Containerization Strategy Rollout
#

FROM sentinelgrid/api-base:latest

# Install service-specific dependencies
USER root
COPY agents/mcp_server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt
USER sentinelgrid

# Copy shared libs
COPY libs ./libs

# Copy application code
COPY agents/mcp_server/app ./app

# Set Python path
ENV PYTHONPATH=/app:/app/libs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
