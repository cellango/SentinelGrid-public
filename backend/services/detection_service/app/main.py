"""Detection Service - Main application."""

import logging
import atexit
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, Base
from app.api import rules
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    logger.info("Starting Detection Service...")
    
    # Start scheduler for periodic rule evaluation
    start_scheduler()
    
    # Register cleanup
    atexit.register(stop_scheduler)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Detection Service...")
    stop_scheduler()


app = FastAPI(
    title="SentinelGrid Detection Service",
    description="Detection rules engine for security alerts",
    version=settings.VERSION,
    lifespan=lifespan,
)

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
