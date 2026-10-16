"""Sync Job Management API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional

from app.models.sync_jobs import (
    CreateSyncJobRequest,
    CreateSyncJobResponse,
    JobStatusResponse,
    ScheduleSyncJobRequest,
    ScheduleResponse,
    SyncType,
    SyncDirection,
    JobSchedule,
    JobStatus
)
from app.services.sync_job_manager import SyncJobManager
from app.services.integration_manager import IntegrationManager
from app.services.keycloak_client import KeycloakClient
from app.api.auth import get_keycloak_client
from app.api.request_context import RequestContext, get_current_request_context
from app.services.connector_framework import SyncDirection as ConnectorSyncDirection, SyncStatus as ConnectorSyncStatus

router = APIRouter(prefix="/internal/iam/sync-jobs", tags=["sync-jobs"])


def _resolve_tenant_id(
    request_context: RequestContext,
    requested_tenant_id: Optional[str] = None,
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if requested_tenant_id is not None and requested_tenant_id != authenticated_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


def get_integration_manager(
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> IntegrationManager:
    """Get integration manager instance."""
    return IntegrationManager(keycloak_client)


def get_sync_job_manager(
    integration_manager: IntegrationManager = Depends(get_integration_manager)
) -> SyncJobManager:
    """Get sync job manager instance."""
    return SyncJobManager(integration_manager)


@router.post("/", response_model=CreateSyncJobResponse)
async def create_sync_job(
    request: CreateSyncJobRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> CreateSyncJobResponse:
    """Create a new sync job."""
    try:
        direction = ConnectorSyncDirection(request.direction.value)
        tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        
        result = job_manager.create_sync_job(
            integration_id=request.integration_id,
            sync_type=request.sync_type.value,
            direction=direction,
            filters=request.filters,
            tenant_id=tenant_id
        )
        
        return CreateSyncJobResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating sync job: {str(e)}")


@router.post("/{job_id}/execute")
async def execute_sync_job(
    job_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> Dict[str, Any]:
    """Execute a sync job."""
    try:
        result = job_manager.execute_sync_job(job_id, tenant_id=str(request_context.tenant_id))
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing sync job: {str(e)}")


@router.get("/", response_model=List[JobStatusResponse])
async def list_jobs(
    integration_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> List[JobStatusResponse]:
    """List sync jobs."""
    try:
        status_enum = ConnectorSyncStatus(status) if status else None
        resolved_tenant_id = _resolve_tenant_id(request_context, tenant_id)
        
        jobs = job_manager.list_jobs(
            integration_id=integration_id,
            status=status_enum,
            tenant_id=resolved_tenant_id,
            limit=limit
        )
        
        return [JobStatusResponse(**job) for job in jobs]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing jobs: {str(e)}")


@router.post("/schedules", response_model=ScheduleResponse)
async def schedule_sync_job(
    request: ScheduleSyncJobRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> ScheduleResponse:
    """Schedule a recurring sync job."""
    try:
        direction = ConnectorSyncDirection(request.direction.value)
        tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        
        result = job_manager.schedule_sync_job(
            integration_id=request.integration_id,
            schedule_type=JobSchedule(request.schedule_type.value),
            sync_type=request.sync_type.value,
            direction=direction,
            cron_expression=request.cron_expression,
            filters=request.filters,
            tenant_id=tenant_id
        )
        
        return ScheduleResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling sync job: {str(e)}")


@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(
    integration_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> List[ScheduleResponse]:
    """List scheduled sync jobs."""
    try:
        resolved_tenant_id = _resolve_tenant_id(request_context, tenant_id)
        schedules = job_manager.list_schedules(
            integration_id=integration_id,
            tenant_id=resolved_tenant_id
        )
        
        return [ScheduleResponse(**schedule) for schedule in schedules]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing schedules: {str(e)}")


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> ScheduleResponse:
    """Get a specific schedule."""
    try:
        schedule = job_manager.get_schedule(schedule_id, tenant_id=str(request_context.tenant_id))
        if not schedule:
            raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
        
        return ScheduleResponse(**schedule)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting schedule: {str(e)}")


@router.put("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    updates: Dict[str, Any],
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> ScheduleResponse:
    """Update a schedule."""
    try:
        result = job_manager.update_schedule(
            schedule_id,
            updates,
            tenant_id=str(request_context.tenant_id),
        )
        return ScheduleResponse(**result)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating schedule: {str(e)}")


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> Dict[str, Any]:
    """Delete a schedule."""
    try:
        result = job_manager.delete_schedule(schedule_id, tenant_id=str(request_context.tenant_id))
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/statistics")
async def get_sync_statistics(
    integration_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> Dict[str, Any]:
    """Get sync statistics."""
    try:
        result = job_manager.get_sync_statistics(
            integration_id=integration_id,
            days=days,
            tenant_id=str(request_context.tenant_id),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> JobStatusResponse:
    """Get status of a sync job."""
    try:
        result = job_manager.get_job_status(job_id, tenant_id=str(request_context.tenant_id))
        return JobStatusResponse(**result)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/retry")
async def retry_failed_job(
    job_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    job_manager: SyncJobManager = Depends(get_sync_job_manager)
) -> Dict[str, Any]:
    """Retry a failed sync job."""
    try:
        result = job_manager.retry_failed_job(job_id, tenant_id=str(request_context.tenant_id))
        return result
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrying job: {str(e)}")
