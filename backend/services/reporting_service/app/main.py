"""Reporting Service - Main application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api import reports, templates, scheduled_reports, shares
from app.core.database import get_db
from app.services.observability import PROMETHEUS_MEDIA_TYPE, runtime_metrics

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SentinelGrid Reporting Service",
    description="Report generation and management service",
    version=settings.VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(templates.router, prefix="/api/v1/reports/templates", tags=["templates"])
app.include_router(scheduled_reports.router, prefix="/api/v1/reports/scheduled", tags=["scheduled-reports"])
app.include_router(shares.router, prefix="/api/v1", tags=["shares"])

# Serve generated reports from the storage path (used by download URLs)
app.mount("/reports", StaticFiles(directory=settings.REPORT_STORAGE_PATH), name="reports")


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "reporting-service"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION
    }


def _metrics_response(format: str | None = None):
    if format == "prometheus":
        return PlainTextResponse(runtime_metrics.prometheus_text(), media_type=PROMETHEUS_MEDIA_TYPE)
    return runtime_metrics.snapshot()


@app.get("/metrics")
def metrics(format: str | None = None):
    """Lightweight runtime metrics for reporting and compliance report generation."""
    return _metrics_response(format)


@app.get("/metrics/prometheus")
def metrics_prometheus():
    """Prometheus exposition for production scraping."""
    return _metrics_response("prometheus")


@app.on_event("startup")
async def startup_event():
    """Seed standard templates and restore scheduled reports on startup."""
    try:
        from app.services.template_seeder import seed_standard_templates
        from app.core.database import get_db
        from app.models.report import ReportTemplate
        from app.services.scheduler import get_scheduler
        
        db = next(get_db())
        try:
            # Seed templates
            seed_standard_templates(db)
            
            # Restore scheduled reports from templates
            scheduler = get_scheduler()
            templates_with_schedule = db.query(ReportTemplate).filter(
                ReportTemplate.schedule.isnot(None)
            ).all()
            
            for template in templates_with_schedule:
                schedule = template.schedule
                if schedule and schedule.get('enabled', False):
                    # Get tenant_id from template (or use system templates for all tenants)
                    # For now, only schedule tenant-specific templates
                    if template.tenant_id:
                        scheduler.schedule_report(
                            template,
                            template.tenant_id,
                            schedule
                        )
                        logger.info(f"Restored scheduled report for template {template.id}")
            
        except Exception as e:
            logger.error(f"Failed to seed templates or restore schedules: {e}", exc_info=True)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not initialize on startup: {e}. This is OK if database is not ready.")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler on app shutdown."""
    from app.services.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduler.shutdown()
