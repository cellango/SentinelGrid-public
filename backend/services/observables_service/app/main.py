"""Observables Service - Track and enrich observables via Cortex."""

import logging
from typing import List
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_tenant_session
from app.core.security import verify_internal_token, get_tenant_id
from app.models import (
    ObservableCreate,
    ObservableResponse,
    ObservableUpdate,
    ObservableSearchRequest,
    EnrichmentRequest,
    BulkObservableCreate,
    AnalyzerJobResponse,
)
from app.services.observable_tracker import ObservableTracker
from app.services.enrichment_engine import EnrichmentEngine

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SentinelGrid Observables Service",
    description="Observable tracking and enrichment via Cortex",
    version=settings.VERSION
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "observables-service"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.post("/observables", response_model=ObservableResponse)
async def create_observable(
    observable: ObservableCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_tenant_session),
    _: bool = Depends(verify_internal_token),
):
    """
    Create a new observable.
    
    If auto_enrich is True, the observable will be automatically enriched
    via Cortex analyzers.
    """
    try:
        tracker = ObservableTracker(db)
        
        if observable.auto_enrich:
            result = await tracker.create_and_enrich(tenant_id, observable)
        else:
            result = tracker.create_observable(tenant_id, observable)
        
        return ObservableResponse.from_orm(result)
    
    except Exception as e:
        logger.error(f"Failed to create observable: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create observable: {str(e)}"
        )


@app.post("/observables/bulk", response_model=List[ObservableResponse])
async def bulk_create_observables(
    request: BulkObservableCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_tenant_session),
    _: bool = Depends(verify_internal_token),
):
    """Create multiple observables in bulk."""
    try:
        tracker = ObservableTracker(db)
        results = await tracker.bulk_create_and_enrich(tenant_id, request.observables)
        return [ObservableResponse.from_orm(r) for r in results]
    
    except Exception as e:
        logger.error(f"Failed to bulk create observables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create observables: {str(e)}"
        )


@app.get("/observables/{observable_id}", response_model=ObservableResponse)
def get_observable(
    observable_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_tenant_session),
    _: bool = Depends(verify_internal_token),
):
    """Get an observable by ID."""
    tracker = ObservableTracker(db)
    observable = tracker.get_observable(tenant_id, observable_id)
    
    if not observable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observable {observable_id} not found"
        )
    
    return ObservableResponse.from_orm(observable)


@app.post("/observables/search", response_model=List[ObservableResponse])
def search_observables(
    request: ObservableSearchRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_tenant_session),
    _: bool = Depends(verify_internal_token),
):
    """Search observables with filters."""
    tracker = ObservableTracker(db)
    observables = tracker.search_observables(
        tenant_id=tenant_id,
        observable_type=request.observable_type.value if request.observable_type else None,
        value_pattern=request.value,
        enrichment_status=request.enrichment_status.value if request.enrichment_status else None,
        source_event_id=request.source_event_id,
        limit=request.limit,
        offset=request.offset,
    )
    
    return [ObservableResponse.from_orm(obs) for obs in observables]


@app.post("/observables/{observable_id}/enrich", response_model=ObservableResponse)
async def enrich_observable(
    observable_id: UUID,
    request: EnrichmentRequest = None,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_tenant_session),
    _: bool = Depends(verify_internal_token),
):
    """Enrich an observable using Cortex analyzers."""
    tracker = ObservableTracker(db)
    
    # Verify observable exists and belongs to tenant
    observable = tracker.get_observable(tenant_id, observable_id)
    if not observable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observable {observable_id} not found"
        )
    
    try:
        engine = EnrichmentEngine(db)
        analyzer_ids = request.analyzer_ids if request else None
        result = await engine.enrich_observable(
            observable_id=observable_id,
            analyzer_ids=analyzer_ids,
            force=True,
        )
        return ObservableResponse.from_orm(result)
    
    except Exception as e:
        logger.error(f"Failed to enrich observable {observable_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enrich observable: {str(e)}"
        )


@app.get("/observables/{observable_id}/analyzers", response_model=List[AnalyzerJobResponse])
def get_observable_analyzers(
    observable_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_tenant_session),
    _: bool = Depends(verify_internal_token),
):
    """Get all analyzer jobs for an observable."""
    from app.models import ObservableAnalyzer
    
    # Verify observable exists and belongs to tenant
    tracker = ObservableTracker(db)
    observable = tracker.get_observable(tenant_id, observable_id)
    if not observable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observable {observable_id} not found"
        )
    
    analyzers = db.query(ObservableAnalyzer).filter(
        ObservableAnalyzer.observable_id == observable_id
    ).all()
    
    return [AnalyzerJobResponse.from_orm(a) for a in analyzers]


@app.patch("/observables/{observable_id}", response_model=ObservableResponse)
def update_observable(
    observable_id: UUID,
    update_data: ObservableUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_tenant_session),
    _: bool = Depends(verify_internal_token),
):
    """Update an observable."""
    tracker = ObservableTracker(db)
    observable = tracker.get_observable(tenant_id, observable_id)
    
    if not observable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observable {observable_id} not found"
        )
    
    # Update fields
    if update_data.tlp_level is not None:
        observable.tlp_level = update_data.tlp_level
    
    if update_data.enrichment_status is not None:
        observable.enrichment_status = update_data.enrichment_status.value
    
    if update_data.enrichment_data is not None:
        observable.enrichment_data = update_data.enrichment_data
    
    db.commit()
    db.refresh(observable)
    
    return ObservableResponse.from_orm(observable)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
