FROM sentinelgrid/api-base:latest

WORKDIR /app

COPY libs ./libs

ENV PYTHONPATH=/app/libs

EXPOSE 8000

CMD ["uvicorn", "sg_agent_runtime.service:app", "--host", "0.0.0.0", "--port", "8000"]
