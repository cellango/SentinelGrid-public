"""Job enqueue/status endpoints for async scanners."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session
from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant

router = APIRouter()


class JobCreate(BaseModel):
    tenant_id: Optional[str] = None
    job_type: str
    payload: dict = {}


class JobResponse(BaseModel):
    id: str
    tenant_id: Optional[str]
    job_type: str
    status: str
    attempts: int
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _row_to_job(row) -> JobResponse:
    return JobResponse(
        id=str(row.id),
        tenant_id=str(row.tenant_id) if row.tenant_id else None,
        job_type=row.job_type,
        status=row.status,
        attempts=row.attempts,
        error=row.error,
        started_at=str(row.started_at) if row.started_at else None,
        finished_at=str(row.finished_at) if row.finished_at else None,
        created_at=str(row.created_at) if row.created_at else None,
        updated_at=str(row.updated_at) if row.updated_at else None,
    )


@router.post("", response_model=JobResponse, tags=["jobs"])
def enqueue_job(job: JobCreate, db: Session = Depends(get_tenant_session), tenant_id: str = Depends(get_current_tenant)):
    """Enqueue a job. tenant_id defaults to current tenant if not provided."""
    target_tenant = tenant_id  # override any provided tenant_id for isolation
    result = db.execute(
        text(
            """
            INSERT INTO jobs (tenant_id, job_type, payload, status, attempts, max_attempts)
            VALUES (:tenant_id, :job_type, :payload, 'queued', 0, 5)
            RETURNING id, tenant_id, job_type, status, attempts, error, started_at, finished_at, created_at, updated_at
            """
        ),
        {"tenant_id": target_tenant, "job_type": job.job_type, "payload": job.payload},
    ).first()
    db.commit()
    return _row_to_job(result)


@router.get("/{job_id}", response_model=JobResponse, tags=["jobs"])
def get_job(job_id: str, db: Session = Depends(get_tenant_session), tenant_id: str = Depends(get_current_tenant)):
    row = db.execute(
        text(
            """
            SELECT id, tenant_id, job_type, status, attempts, error, started_at, finished_at, created_at, updated_at
            FROM jobs
            WHERE id = :id AND (tenant_id = :tenant_id OR tenant_id IS NULL)
            """
        ),
        {"id": job_id, "tenant_id": tenant_id},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return _row_to_job(row)


@router.get("", response_model=List[JobResponse], tags=["jobs"])
def list_jobs(
    db: Session = Depends(get_tenant_session),
    tenant_id: str = Depends(get_current_tenant),
    job_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    params = {
        "tenant_id": tenant_id,
        "job_type": job_type,
        "status": status,
        "limit": limit,
    }
    rows = db.execute(
        text(
            """
            SELECT id, tenant_id, job_type, status, attempts, error, started_at, finished_at, created_at, updated_at
            FROM jobs
            WHERE (tenant_id = :tenant_id OR tenant_id IS NULL)
              AND (:job_type IS NULL OR job_type = :job_type)
              AND (:status IS NULL OR status = :status)
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        params,
    ).fetchall()
    return [_row_to_job(r) for r in rows]
