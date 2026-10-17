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
    JobStatus,
)
from app.services.sync_job_manager import SyncJobManager
from app.services.integration_manager import IntegrationManager
from app.services.keycloak_client import KeycloakClient
from app.api.auth import get_keycloak_client
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    ensure_request_has_any_role,
)
from app.services.connector_framework import (
    SyncDirection as ConnectorSyncDirection,
    SyncStatus as ConnectorSyncStatus,
)

router = APIRouter(prefix="/internal/iam/sync-jobs", tags=["sync-jobs"])


def _resolve_tenant_id(
    request_context: RequestContext, requested_tenant_id: Optional[str] = None
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if (
        requested_tenant_id is not None
        and requested_tenant_id != authenticated_tenant_id
    ):
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


def get_integration_manager() -> IntegrationManager:
    return IntegrationManager(None)


def get_sync_job_manager(
    integration_manager: IntegrationManager = Depends(get_integration_manager),
) -> SyncJobManager:
    """Get sync job manager instance."""
    return SyncJobManager(integration_manager)


@router.post("/", response_model=CreateSyncJobResponse)
async def create_sync_job(
    request: CreateSyncJobRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> CreateSyncJobResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.post("/{job_id}/execute")
async def execute_sync_job(
    job_id: str, request_context: RequestContext = Depends(get_current_request_context)
) -> Dict[str, Any]:
    _resolve_tenant_id(request_context, None)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.get("/", response_model=List[JobStatusResponse])
async def list_jobs(
    integration_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    request_context: RequestContext = Depends(get_current_request_context),
) -> List[JobStatusResponse]:
    _resolve_tenant_id(request_context, tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.post("/schedules", response_model=ScheduleResponse)
async def schedule_sync_job(
    request: ScheduleSyncJobRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> ScheduleResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(
    integration_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
) -> List[ScheduleResponse]:
    _resolve_tenant_id(request_context, tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
) -> ScheduleResponse:
    _resolve_tenant_id(request_context, None)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.put("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    updates: Dict[str, Any],
    request_context: RequestContext = Depends(get_current_request_context),
) -> ScheduleResponse:
    _resolve_tenant_id(request_context, None)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
) -> Dict[str, Any]:
    _resolve_tenant_id(request_context, None)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.get("/statistics")
async def get_sync_statistics(
    integration_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    request_context: RequestContext = Depends(get_current_request_context),
) -> Dict[str, Any]:
    _resolve_tenant_id(request_context, None)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str, request_context: RequestContext = Depends(get_current_request_context)
) -> JobStatusResponse:
    _resolve_tenant_id(request_context, None)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )


@router.post("/{job_id}/retry")
async def retry_failed_job(
    job_id: str, request_context: RequestContext = Depends(get_current_request_context)
) -> Dict[str, Any]:
    _resolve_tenant_id(request_context, None)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity sync jobs require durable authority, storage and verified provider effects",
    )
