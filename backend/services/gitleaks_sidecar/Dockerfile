FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq && apt-get install -y -qq wget ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# Install gitleaks binary (arm64 build to match dev env)
ENV GITLEAKS_VERSION=8.18.2
RUN wget -q https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_arm64.tar.gz \
    && tar -xzf gitleaks_${GITLEAKS_VERSION}_linux_arm64.tar.gz -C /usr/local/bin gitleaks \
    && rm gitleaks_${GITLEAKS_VERSION}_linux_arm64.tar.gz \
    && chmod +x /usr/local/bin/gitleaks

RUN pip install --no-cache-dir fastapi uvicorn

WORKDIR /app
COPY app /app/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
