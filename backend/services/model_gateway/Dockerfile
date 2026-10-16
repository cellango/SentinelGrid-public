#
# Model Gateway Service
# Uses: sentinelgrid/api-ml (includes FastAPI, SQLAlchemy, transformers, torch, etc.)
# Updated: Dec 3, 2025 - Containerization Strategy Phase 2 POC
#

ARG SENTINELGRID_API_ML_IMAGE=sentinelgrid/api-ml:latest
FROM ${SENTINELGRID_API_ML_IMAGE}

# Switch to root for installations
USER root

# Git ingestion uses the git CLI when GitPython falls back to subprocess.
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Install service-specific dependencies
# Common deps (FastAPI, SQLAlchemy) and ML deps (transformers, torch) already in base
COPY requirements-specific.txt .
RUN pip install --no-cache-dir --default-timeout=300 -r requirements-specific.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x scripts/*.py

# Create model directories
RUN mkdir -p /models/base /models/adapters && \
    chown -R sentinelgrid:sentinelgrid /models

# Switch back to non-root user
USER sentinelgrid

# Environment variables
ENV BASE_MODEL_PATH=/models/base \
    ADAPTER_STORAGE_PATH=/models/adapters \
    LLM_RUNTIME=transformers \
    PYTHONPATH=/app \
    SENTENCE_TRANSFORMERS_HOME=/models/cache

# Pre-download step removed to keep builds fast/robust; model downloads at runtime
ENV HF_HUB_DOWNLOAD_TIMEOUT=120
RUN mkdir -p /models/cache

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
