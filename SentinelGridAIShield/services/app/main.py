"""
SentinelGridAIShield Services
Merged API backend + guardrails detection
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import ai_apps, ai_policies, ai_events, telemetry, ai_assistant, gateway_config, internal_auth, internal_keys
from app.core.database import engine
from app.core.config import settings
from app.guardrails import pii, injection, secrets, validation
from app import models


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Keep local development simple by creating the schema on startup.
    if not settings.SKIP_DB_INIT_ON_STARTUP:
        models.Base.metadata.create_all(bind=engine)
    yield

# Create FastAPI app
app = FastAPI(
    title="SentinelGridAIShield Services",
    description="AI Security API + Guardrails Detection",
    version="1.0.0",
    lifespan=lifespan,
)

if settings.CORS_ORIGINS:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Internal-Service-Token", "X-Tenant-ID"],
    )

# API routes
app.include_router(ai_apps.router, prefix="/api/v1/ai-apps", tags=["AI Apps"])
app.include_router(ai_policies.router, prefix="/api/v1/ai-policies", tags=["AI Policies"])
app.include_router(ai_events.router, prefix="/api/v1/ai-events", tags=["AI Events"])
app.include_router(telemetry.router, prefix="/api/v1/telemetry", tags=["Telemetry"])
app.include_router(ai_assistant.router, prefix="/api/v1/ai-assistant", tags=["AI Assistant"])
app.include_router(gateway_config.router, prefix="/api/v1/gateway", tags=["Gateway Config"])
app.include_router(internal_auth.router)
app.include_router(internal_keys.router)

# Guardrails routes
app.include_router(pii.router, prefix="/api/v1/guardrails", tags=["Guardrails"])
app.include_router(injection.router, prefix="/api/v1/guardrails", tags=["Guardrails"])
app.include_router(secrets.router, prefix="/api/v1/guardrails", tags=["Guardrails"])
app.include_router(validation.router, prefix="/api/v1/guardrails", tags=["Guardrails"])

@app.get("/")
def root():
    return {
        "service": "SentinelGridAIShield Services",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
