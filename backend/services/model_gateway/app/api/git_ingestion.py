"""Git ingestion API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.requests import Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.core.database import get_current_tenant, get_superadmin_db, get_tenant_session
from app.services.git_data_ingestion_service import GitDataIngestionService
from app.services.scheduled_ingestion_service import ScheduledIngestionService
from app.models.git_repos import GitRepository

router = APIRouter(prefix="/internal/llm/git-ingestion", tags=["Git Ingestion"])


class IngestRepoRequest(BaseModel):
    """Request model for manual repository ingestion."""
    repo_url: str = Field(..., description="Git repository URL")
    repo_type: str = Field("customer", description="'customer' or 'global'")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (required for customer repos)")
    branch: str = Field("main", description="Git branch to checkout")
    paths: Optional[list[str]] = Field(None, description="Optional paths to process")


class WebhookRequest(BaseModel):
    """Request model for git webhook."""
    payload: Dict[str, Any] = Field(..., description="Webhook payload from git provider")
    repo_type: str = Field("customer", description="'customer' or 'global'")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (required for customer repos)")


def _resolve_effective_tenant_id(
    repo_type: str,
    requested_tenant_id: Optional[str],
    current_tenant_id: UUID,
) -> Optional[str]:
    normalized_repo_type = (repo_type or "customer").lower()

    if normalized_repo_type == "global":
        return None

    effective_tenant_id = requested_tenant_id or str(current_tenant_id)
    if str(effective_tenant_id) != str(current_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )

    return str(current_tenant_id)


def _is_platform_operation(x_platform_operation: Optional[str]) -> bool:
    return str(x_platform_operation or "").strip().lower() in {"1", "true", "yes"}


def _select_repo_db(
    repo_type: str,
    x_platform_operation: Optional[str],
    tenant_db: Session,
    superadmin_db: Session,
) -> Session:
    normalized_repo_type = (repo_type or "customer").lower()
    if normalized_repo_type == "global":
        if not _is_platform_operation(x_platform_operation):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Global repository operations require X-Platform-Operation: true",
            )
        return superadmin_db
    return tenant_db


def _repo_metadata(repo: GitRepository) -> Dict[str, Any]:
    metadata = repo.metadata_json or {}
    return metadata if isinstance(metadata, dict) else {}


def _repo_name_from_url(repo_url: str) -> str:
    repo_name = repo_url.rstrip("/").split("/")[-1]
    return repo_name[:-4] if repo_name.endswith(".git") else repo_name


def _repo_response_payload(repo: GitRepository) -> Dict[str, Any]:
    metadata = _repo_metadata(repo)
    last_ingested_at = metadata.get("last_ingested_at")
    if hasattr(last_ingested_at, "isoformat"):
        last_ingested_at = last_ingested_at.isoformat()

    return {
        "id": str(repo.id),
        "tenant_id": str(repo.tenant_id) if repo.tenant_id else None,
        "repo_url": repo.url,
        "repo_type": metadata.get("repo_type") or ("global" if repo.tenant_id is None else "customer"),
        "branch": repo.branch,
        "is_active": (repo.status or "active") == "active",
        "last_ingested_at": last_ingested_at,
        "last_ingestion_status": metadata.get("last_ingestion_status"),
    }


def _build_repo_metadata(
    repo_type: str,
    paths: Optional[List[str]],
    webhook_secret: Optional[str],
    existing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata = dict(existing or {})
    metadata["repo_type"] = (repo_type or "customer").lower()
    if paths is not None:
        metadata["paths"] = paths
    if webhook_secret is not None:
        metadata["webhook_secret"] = webhook_secret
    return metadata


@router.post("/ingest", response_model=Dict[str, Any])
def ingest_from_repo(
    request: IngestRepoRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    tenant_db: Session = Depends(get_tenant_session),
    superadmin_db: Session = Depends(get_superadmin_db),
    x_platform_operation: Optional[str] = Header(None, alias="X-Platform-Operation"),
):
    """Manually trigger ingestion from a git repository."""
    db = _select_repo_db(request.repo_type, x_platform_operation, tenant_db, superadmin_db)
    service = GitDataIngestionService(db_session=db)

    effective_tenant_id = _resolve_effective_tenant_id(
        request.repo_type,
        request.tenant_id,
        current_tenant_id,
    )
    
    result = service.ingest_from_repo(
        repo_url=request.repo_url,
        repo_type=request.repo_type,
        tenant_id=effective_tenant_id,
        branch=request.branch,
        paths=request.paths
    )
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Ingestion failed")
        )
    
    return result


@router.post("/webhook/github", response_model=Dict[str, Any])
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    current_tenant_id: UUID = Depends(get_current_tenant),
    tenant_db: Session = Depends(get_tenant_session),
    superadmin_db: Session = Depends(get_superadmin_db),
    x_platform_operation: Optional[str] = Header(None, alias="X-Platform-Operation"),
    tenant_id: Optional[str] = None,
    repo_type: str = "customer"
):
    """Handle GitHub webhook events."""
    if x_github_event != "push":
        return {"status": "skipped", "message": f"Event type {x_github_event} not processed"}
    
    payload = await request.json()
    effective_tenant_id = _resolve_effective_tenant_id(repo_type, tenant_id, current_tenant_id)
    db = _select_repo_db(repo_type, x_platform_operation, tenant_db, superadmin_db)
    service = GitDataIngestionService(db_session=db)
    
    result = service.process_webhook_payload(
        webhook_data=payload,
        repo_type=repo_type,
        tenant_id=effective_tenant_id
    )
    
    return result


@router.post("/webhook/gitlab", response_model=Dict[str, Any])
async def gitlab_webhook(
    request: Request,
    x_gitlab_event: Optional[str] = Header(None),
    current_tenant_id: UUID = Depends(get_current_tenant),
    tenant_db: Session = Depends(get_tenant_session),
    superadmin_db: Session = Depends(get_superadmin_db),
    x_platform_operation: Optional[str] = Header(None, alias="X-Platform-Operation"),
    tenant_id: Optional[str] = None,
    repo_type: str = "customer"
):
    """Handle GitLab webhook events."""
    if x_gitlab_event != "Push Hook":
        return {"status": "skipped", "message": f"Event type {x_gitlab_event} not processed"}
    
    payload = await request.json()
    effective_tenant_id = _resolve_effective_tenant_id(repo_type, tenant_id, current_tenant_id)
    db = _select_repo_db(repo_type, x_platform_operation, tenant_db, superadmin_db)
    service = GitDataIngestionService(db_session=db)
    
    result = service.process_webhook_payload(
        webhook_data=payload,
        repo_type=repo_type,
        tenant_id=effective_tenant_id
    )
    
    return result


@router.post("/webhook/generic", response_model=Dict[str, Any])
def generic_webhook(
    request: WebhookRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    tenant_db: Session = Depends(get_tenant_session),
    superadmin_db: Session = Depends(get_superadmin_db),
    x_platform_operation: Optional[str] = Header(None, alias="X-Platform-Operation"),
):
    """Handle generic git webhook (for custom integrations)."""
    effective_tenant_id = _resolve_effective_tenant_id(
        request.repo_type,
        request.tenant_id,
        current_tenant_id,
    )
    db = _select_repo_db(request.repo_type, x_platform_operation, tenant_db, superadmin_db)
    service = GitDataIngestionService(db_session=db)
    
    result = service.process_webhook_payload(
        webhook_data=request.payload,
        repo_type=request.repo_type,
        tenant_id=effective_tenant_id
    )
    
    return result


@router.get("/repos", response_model=List[Dict[str, Any]])
def list_registered_repos(
    tenant_id: Optional[str] = None,
    repo_type: Optional[str] = None,
    current_tenant_id: UUID = Depends(get_current_tenant),
    tenant_db: Session = Depends(get_tenant_session),
    superadmin_db: Session = Depends(get_superadmin_db),
    x_platform_operation: Optional[str] = Header(None, alias="X-Platform-Operation"),
):
    """List registered repositories for ingestion."""
    from sqlalchemy import or_, select
    db = _select_repo_db(repo_type or "customer", x_platform_operation, tenant_db, superadmin_db)

    normalized_repo_type = (repo_type or "").lower()
    if normalized_repo_type == "global":
        stmt = select(GitRepository).where(
            GitRepository.status == "active",
            GitRepository.tenant_id.is_(None),
        )
    else:
        effective_tenant_id = _resolve_effective_tenant_id(
            normalized_repo_type or "customer",
            tenant_id,
            current_tenant_id,
        )
        stmt = select(GitRepository).where(GitRepository.status == "active")
        tenant_uuid = UUID(effective_tenant_id)
        if tenant_id or normalized_repo_type == "customer":
            stmt = stmt.where(GitRepository.tenant_id == tenant_uuid)
        else:
            stmt = stmt.where(
                or_(GitRepository.tenant_id == tenant_uuid, GitRepository.tenant_id.is_(None))
            )

    repos = db.execute(stmt).scalars().all()

    return [_repo_response_payload(repo) for repo in repos]


@router.post("/repos/register", response_model=Dict[str, Any])
def register_repo(
    repo_url: str,
    repo_type: str = "customer",
    tenant_id: Optional[str] = None,
    branch: str = "main",
    paths: Optional[List[str]] = None,
    webhook_secret: Optional[str] = None,
    current_tenant_id: UUID = Depends(get_current_tenant),
    tenant_db: Session = Depends(get_tenant_session),
    superadmin_db: Session = Depends(get_superadmin_db),
    x_platform_operation: Optional[str] = Header(None, alias="X-Platform-Operation"),
):
    """Register a repository for automated ingestion."""
    effective_tenant_id = _resolve_effective_tenant_id(repo_type, tenant_id, current_tenant_id)
    db = _select_repo_db(repo_type, x_platform_operation, tenant_db, superadmin_db)
    
    # Check if already registered
    from sqlalchemy import select
    stmt = select(GitRepository).where(GitRepository.url == repo_url)
    if effective_tenant_id:
        stmt = stmt.where(GitRepository.tenant_id == UUID(effective_tenant_id))
    else:
        stmt = stmt.where(GitRepository.tenant_id.is_(None))
    
    existing = db.execute(stmt).scalar_one_or_none()
    
    if existing:
        # Update existing
        existing.name = _repo_name_from_url(repo_url)
        existing.url = repo_url
        existing.branch = branch
        existing.status = "active"
        existing.metadata_json = _build_repo_metadata(
            repo_type,
            paths,
            webhook_secret,
            _repo_metadata(existing),
        )
        db.commit()
        db.refresh(existing)
        
        return {
            "status": "updated",
            "id": str(existing.id),
            "repo_url": repo_url
        }
    
    # Create new
    repo = GitRepository(
        tenant_id=UUID(effective_tenant_id) if effective_tenant_id else None,
        name=_repo_name_from_url(repo_url),
        url=repo_url,
        branch=branch,
        status="active",
        metadata_json=_build_repo_metadata(repo_type, paths, webhook_secret),
    )
    
    db.add(repo)
    db.commit()
    db.refresh(repo)
    
    return {
        "status": "registered",
        "id": str(repo.id),
        "repo_url": repo_url,
        "repo_type": repo_type,
        "webhook_url": f"/internal/llm/git-ingestion/webhook/generic?tenant_id={effective_tenant_id or 'global'}"
    }


@router.post("/poll", response_model=Dict[str, Any])
def poll_all_repos(
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Manually trigger polling of all active repositories."""
    service = ScheduledIngestionService(db_session=db)
    results = service.poll_all_active_repos(tenant_id=str(current_tenant_id))
    return results
