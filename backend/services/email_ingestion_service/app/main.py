"""Main FastAPI application for Email Ingestion Service."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api import phishing

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SentinelGrid Email Ingestion Service",
    description="Email ingestion service for phishing email triage (Hero Flow 3)",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")


# Register routers
app.include_router(phishing.router)
from app.api import containment
app.include_router(containment.router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "status": "ok",
        "service": "email-ingestion-service",
        "version": "0.1.0"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "email-ingestion-service",
        "version": "0.1.0"
    }
