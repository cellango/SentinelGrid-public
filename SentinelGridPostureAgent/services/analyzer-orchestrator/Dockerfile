FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
COPY services/analyzer-orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (relative to build context: SentinelGridPostureAgent/)
COPY services/analyzer-orchestrator/app/ ./app/

# Copy shared modules and analyzers (relative to build context)
COPY shared /app/shared
COPY analyzers /app/analyzers
COPY tools /app/tools

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

