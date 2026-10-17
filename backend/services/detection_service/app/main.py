"""Detection Service - Main application."""

import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.security import require_detection_request
from app.api import rules

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Schema adoption requires the reviewed model/Flyway contract; no runtime DDL.


@asynccontextmanager
async def lifespan(app: FastAPI):
    """HTTP source admission only; never auto-start or claim scheduler readiness."""
    yield


app = FastAPI(
    title="SentinelGrid Detection Service",
    description="Detection rules engine for security alerts",
    version=settings.VERSION,
    lifespan=lifespan,
    dependencies=[Depends(require_detection_request)],
)

app.state.iam_verification_settings = settings.verification_settings()
app.state.detection_principal_settings = settings.principal_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rules.router, prefix="/api/v1")
from app.api import scheduler
app.include_router(scheduler.router, prefix="/api/v1")


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "detection-service"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    from app.services.scheduler import get_scheduler
    
    scheduler = get_scheduler()
    scheduler_status = "running" if scheduler.running else "stopped"
    
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "scheduler": scheduler_status,
    }
