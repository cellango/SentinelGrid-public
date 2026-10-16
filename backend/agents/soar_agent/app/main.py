"""SOAR Agent Service - TheHive + workflow integration."""

from typing import List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import asyncio

from app.core.config import settings
from app.models import (
    Playbook,
    PlaybookCreate,
    PlaybookUpdate,
    PlaybookCopy,
    PlaybookValidationResult,
    PlaybookExecutionCreate,
    PlaybookExecution,
)
from app.services.playbook_service import PlaybookService
from app.core.database import get_tenant_session
from app.core.security import get_current_tenant
from app.api import webhooks
from app.api import ootb_playbooks
# Enrichment functionality (merged from ai_enrichment_agent - Dec 3, 2025)
from app.api import enrichment

app = FastAPI(
    title="SentinelGrid SOAR Agent",
    description="SOAR integration service - Playbook management, execution, and AI-powered enrichment",
    version="0.2.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_playbook_service(db: Session = Depends(get_tenant_session)) -> PlaybookService:
    """Get playbook service."""
    return PlaybookService(db)


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "soar-agent"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "soar-agent"}


# Playbook Management APIs

@app.post("/soar/playbooks", response_model=Playbook, status_code=status.HTTP_201_CREATED)
def create_playbook(
    playbook_data: PlaybookCreate,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service)
):
    """Create a new playbook."""
    try:
        playbook = service.create(tenant_id, playbook_data)
        return playbook
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create playbook: {str(e)}"
        )


@app.get("/soar/playbooks", response_model=List[Playbook])
def list_playbooks(
    category: Optional[str] = None,
    is_template: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service)
):
    """List playbooks for tenant."""
    try:
        playbooks = service.list(
            tenant_id=tenant_id,
            category=category,
            is_template=is_template,
            skip=skip,
            limit=limit
        )
        return playbooks
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list playbooks: {str(e)}"
        )


@app.get("/soar/playbooks/{playbook_id}", response_model=Playbook)
def get_playbook(
    playbook_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service)
):
    """Get playbook by ID."""
    playbook = service.get_by_id(playbook_id, tenant_id)
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )
    return playbook


@app.post("/soar/playbooks/{playbook_id}/copy", response_model=Playbook)
def copy_playbook(
    playbook_id: UUID,
    copy_request: PlaybookCopy,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service),
):
    """Copy/duplicate a playbook."""
    copied = service.copy(playbook_id, tenant_id, copy_request)
    if not copied:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )
    return copied


@app.post("/soar/playbooks/{playbook_id}/approve", response_model=Playbook)
def approve_playbook(
    playbook_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service),
):
    """Approve a playbook (enables it)."""
    updated = service.set_approval_status(playbook_id, tenant_id, approve=True)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")
    return updated


@app.post("/soar/playbooks/{playbook_id}/reject", response_model=Playbook)
def reject_playbook(
    playbook_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service),
):
    """Reject a playbook (disables it)."""
    updated = service.set_approval_status(playbook_id, tenant_id, approve=False)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")
    return updated


@app.post("/soar/playbooks/{playbook_id}/preview", response_model=PlaybookValidationResult)
def preview_playbook(
    playbook_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service),
):
    """Preview/validate a playbook structure."""
    playbook = service.get_by_id(playbook_id, tenant_id)
    if not playbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")
    return service.validate(playbook)


@app.post("/soar/playbooks/{playbook_id}/validate", response_model=PlaybookValidationResult)
def validate_playbook(
    playbook_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service),
):
    """Validate a playbook (alias to preview)."""
    playbook = service.get_by_id(playbook_id, tenant_id)
    if not playbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")
    return service.validate(playbook)


@app.put("/soar/playbooks/{playbook_id}", response_model=Playbook)
def update_playbook(
    playbook_id: UUID,
    playbook_data: PlaybookUpdate,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service)
):
    """Update playbook."""
    playbook = service.update(playbook_id, tenant_id, playbook_data)
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )
    return playbook


@app.delete("/soar/playbooks/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playbook(
    playbook_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service)
):
    """Delete playbook."""
    success = service.delete(playbook_id, tenant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )


@app.post("/soar/playbooks/{playbook_id}/copy", response_model=Playbook, status_code=status.HTTP_201_CREATED)
def copy_playbook(
    playbook_id: UUID,
    copy_request: PlaybookCopy,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service)
):
    """Copy/duplicate a playbook."""
    new_playbook = service.copy(playbook_id, tenant_id, copy_request)
    if not new_playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )
    return new_playbook


@app.post("/soar/playbooks/{playbook_id}/validate", response_model=PlaybookValidationResult)
def validate_playbook(
    playbook_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service)
):
    """Validate playbook structure."""
    playbook = service.get_by_id(playbook_id, tenant_id)
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )
    
    validation_result = service.validate(playbook)
    return validation_result


# Playbook Execution APIs

@app.post("/soar/playbooks/{playbook_id}/execute")
async def execute_playbook(
    playbook_id: UUID,
    execution_request: PlaybookExecutionCreate,
    tenant_id: UUID = Depends(get_current_tenant),
    service: PlaybookService = Depends(get_playbook_service),
    db: Session = Depends(get_tenant_session),
):
    """Execute a playbook."""
    # Verify playbook exists
    playbook = service.get_by_id(playbook_id, tenant_id)
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )
    
    from app.services.playbook_execution_service import PlaybookExecutionService
    exec_service = PlaybookExecutionService(db)
    context = {
        "trigger_type": execution_request.trigger_type,
        "trigger_id": str(execution_request.trigger_id) if execution_request.trigger_id else None,
        "parameters": execution_request.parameters,
        "playbook_version": playbook.version,
    }

    approval_status = "pending" if playbook.requires_approval else "approved"
    if playbook.requires_approval:
        execution = exec_service.create_execution(
            tenant_id=str(tenant_id),
            playbook_id=playbook_id,
            triggered_by="api",
            context={
                **context,
                "requires_approval": True,
            },
        )
        message = "Execution request recorded and awaiting approval before automation can start."
    else:
        execution = await exec_service.execute_playbook(
            tenant_id=str(tenant_id),
            playbook_id=playbook_id,
            triggered_by="api",
            context=context,
        )
        message = (
            "Execution request recorded and pending SOAR worker handoff."
            if execution.status == "pending"
            else "Execution request accepted."
        )

    return {
        "execution_id": str(execution.id),
        "status": execution.status,
        "approval_status": approval_status,
        "workflow_exec_id": getattr(execution, "workflow_exec_id", None),
        "message": message,
    }


@app.get("/soar/executions/{execution_id}", response_model=PlaybookExecution)
def get_execution_status(
    execution_id: UUID,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get playbook execution status."""
    from app.services.playbook_execution_service import PlaybookExecutionService
    
    service = PlaybookExecutionService(db)
    execution = service.get_execution(execution_id, tenant_id)
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return execution


# TheHive Observables & Analyzers APIs

@app.get("/soar/observables/types")
def get_observable_types():
    """Get available observable data types."""
    return {
        "types": [
            {"id": "ip", "label": "IP Address"},
            {"id": "domain", "label": "Domain"},
            {"id": "url", "label": "URL"},
            {"id": "hash_md5", "label": "Hash (MD5)"},
            {"id": "hash_sha1", "label": "Hash (SHA1)"},
            {"id": "hash_sha256", "label": "Hash (SHA256)"},
            {"id": "email", "label": "Email Address"},
            {"id": "filename", "label": "Filename"},
            {"id": "filepath", "label": "File Path"},
            {"id": "registry", "label": "Registry Key"},
            {"id": "user-agent", "label": "User Agent"},
            {"id": "autonomous-system", "label": "Autonomous System"},
        ]
    }


@app.get("/soar/analyzers")
def list_analyzers_sync(data_type: Optional[str] = None):
    """List available TheHive analyzers."""
    from app.services.thehive_service import TheHiveService
    
    service = TheHiveService()
    analyzers = asyncio.run(service.list_analyzers(data_type))
    return {"analyzers": analyzers}


@app.get("/soar/analyzers/{analyzer_id}")
def get_analyzer_details(analyzer_id: str):
    """Get analyzer details."""
    from app.services.thehive_service import TheHiveService
    
    service = TheHiveService()
    analyzers = asyncio.run(service.list_analyzers())
    analyzer = next((a for a in analyzers if a.get("id") == analyzer_id), None)
    
    if not analyzer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analyzer {analyzer_id} not found"
        )
    
    return analyzer


@app.post("/soar/observables")
def create_observable(
    request: dict,
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Create an observable in TheHive."""
    from app.services.thehive_service import TheHiveService
    
    service = TheHiveService()
    observable = asyncio.run(service.create_observable(
        data_type=request.get("data_type"),
        data=request.get("data"),
        tags=request.get("tags", []),
        ioc=request.get("ioc", False),
        sighted=request.get("sighted", False),
        message=request.get("message"),
        case_id=request.get("case_id"),
    ))
    
    return observable


@app.post("/soar/analyzers/{analyzer_id}/run")
def run_analyzer(
    analyzer_id: str,
    request: dict,
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Run an analyzer on an observable."""
    from app.services.thehive_service import TheHiveService
    
    service = TheHiveService()
    job = asyncio.run(service.run_analyzer(
        analyzer_id=analyzer_id,
        observable_id=request.get("observable_id"),
        parameters=request.get("parameters"),
    ))
    
    return job


# Include webhook routers
app.include_router(webhooks.router, prefix="/api/v1", tags=["webhooks"])

# Include phishing containment router
from app.api import phishing_containment
app.include_router(phishing_containment.router)

# Include OOTB playbooks router
app.include_router(ootb_playbooks.router, prefix="/soar", tags=["ootb-playbooks"])

# Include detection events router (webhook receiver for OpenSearch monitors)
from app.api import detection_events
app.include_router(detection_events.router, prefix="/api/v1", tags=["detection-events"])

# Include enrichment router (merged from ai_enrichment_agent - Dec 3, 2025)
app.include_router(enrichment.router, prefix="/api/v1/enrichment", tags=["enrichment"])

# Internal APIs (for other services)

@app.post("/internal/soar/playbooks/{playbook_id}/execute")
def execute_playbook_internal(playbook_id: str, request: dict):
    """Execute a playbook (internal API)."""
    # V1 stub - kept for backward compatibility
    return {
        "execution_id": "exec-1",
        "status": "pending",
        "workflow_exec_id": "wf-run-xyz"
    }
