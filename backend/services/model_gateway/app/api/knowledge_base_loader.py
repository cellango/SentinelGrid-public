"""API endpoints for knowledge base loading."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.core.database import get_current_tenant, get_superadmin_db, get_tenant_session
from app.services.knowledge_base_loader import KnowledgeBaseLoader

router = APIRouter(prefix="/internal/llm/knowledge-base", tags=["Knowledge Base"])


class LoadRequest(BaseModel):
    """Request model for loading knowledge bases."""
    frameworks: list[str] = ["nist", "mitre", "owasp", "playbooks", "soc2"]
    nist_source: Optional[str] = None
    mitre_source: Optional[str] = None
    owasp_source: Optional[str] = None
    playbooks_source: Optional[str] = None
    soc2_source: Optional[str] = None
    async_load: bool = False


class ReportLoadRequest(BaseModel):
    """Request model for loading a generated report into the KB."""
    tenant_id: str
    realm_name: Optional[str] = None
    report_id: str
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    file_path: Optional[str] = None
    sections: List[Dict[str, Any]] = Field(default_factory=list)


def _enforce_same_tenant(requested_tenant_id: str | UUID, current_tenant_id: UUID) -> None:
    if str(requested_tenant_id) != str(current_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )


@router.post("/load", response_model=dict)
def load_knowledge_bases(
    request: LoadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_superadmin_db),
):
    """Load cybersecurity knowledge bases into vector database."""
    loader = KnowledgeBaseLoader(db_session=db)
    
    if request.async_load:
        # Load in background (for large datasets)
        background_tasks.add_task(
            _load_all_background,
            loader,
            request
        )
        return {
            "status": "started",
            "message": "Knowledge base loading started in background"
        }
    else:
        # Load synchronously
        results = _load_frameworks(loader, request)
        
        total_loaded = sum(r["loaded"] for r in results.values())
        total_errors = sum(r["errors"] for r in results.values())
        
        return {
            "status": "completed",
            "results": results,
            "summary": {
                "total_loaded": total_loaded,
                "total_errors": total_errors
            }
        }


def _load_frameworks(loader: KnowledgeBaseLoader, request: LoadRequest) -> dict:
    """Load specified frameworks."""
    results = {}
    
    if "nist" in request.frameworks:
        results["nist"] = loader.load_nist_controls(request.nist_source)
    
    if "mitre" in request.frameworks:
        results["mitre"] = loader.load_mitre_techniques(request.mitre_source)
    
    if "owasp" in request.frameworks:
        results["owasp"] = loader.load_owasp_content(request.owasp_source)
    
    if "playbooks" in request.frameworks:
        results["playbooks"] = loader.load_playbooks(request.playbooks_source)

    if "soc2" in request.frameworks:
        results["soc2"] = loader.load_soc2_content(request.soc2_source)
    
    return results


def _load_all_background(loader: KnowledgeBaseLoader, request: LoadRequest):
    """Background task for loading knowledge bases."""
    try:
        _load_frameworks(loader, request)
    except Exception as e:
        # Log error (in production, consider using proper logging service)
        print(f"Error in background knowledge base loading: {e}")


@router.post("/load/nist", response_model=dict)
def load_nist(
    source: Optional[str] = None,
    db: Session = Depends(get_superadmin_db),
):
    """Load NIST 800-53 controls."""
    loader = KnowledgeBaseLoader(db_session=db)
    result = loader.load_nist_controls(source)
    return result


@router.post("/load/mitre", response_model=dict)
def load_mitre(
    source: Optional[str] = None,
    db: Session = Depends(get_superadmin_db),
):
    """Load MITRE ATT&CK techniques."""
    loader = KnowledgeBaseLoader(db_session=db)
    result = loader.load_mitre_techniques(source)
    return result


@router.post("/load/owasp", response_model=dict)
def load_owasp(
    source: Optional[str] = None,
    db: Session = Depends(get_superadmin_db),
):
    """Load OWASP content."""
    loader = KnowledgeBaseLoader(db_session=db)
    result = loader.load_owasp_content(source)
    return result


@router.post("/load/playbooks", response_model=dict)
def load_playbooks(
    source: Optional[str] = None,
    db: Session = Depends(get_superadmin_db),
):
    """Load SOC playbooks."""
    loader = KnowledgeBaseLoader(db_session=db)
    result = loader.load_playbooks(source)
    return result


@router.post("/load/soc2", response_model=dict)
def load_soc2(
    source: Optional[str] = None,
    db: Session = Depends(get_superadmin_db),
):
    """Load SOC 2 criteria, mappings, and report schema."""
    loader = KnowledgeBaseLoader(db_session=db)
    result = loader.load_soc2_content(source)
    return result


@router.get("/health/soc2", response_model=dict)
def soc2_health(
    tenant_id: str,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Health check to verify SOC 2 KB entries are retrievable via RAG for a tenant.
    Returns ok=true if at least one SOC 2 entry is found.
    """
    _enforce_same_tenant(tenant_id, current_tenant_id)
    loader = KnowledgeBaseLoader(db_session=db)
    results = loader.rag_service.search(
        query="SOC 2 Trust Services",
        tenant_id=tenant_id,
        category="soc2",
        top_k=1
    )
    return {"ok": len(results) > 0, "count": len(results)}


@router.post("/load/report", response_model=dict)
def load_report(
    request: ReportLoadRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Load a generated report (PDF/CSV sections) into the tenant-scoped KB."""
    _enforce_same_tenant(request.tenant_id, current_tenant_id)
    loader = KnowledgeBaseLoader(db_session=db)
    try:
        result = loader.load_report_content(
            tenant_id=request.tenant_id,
            realm_name=request.realm_name,
            report_id=request.report_id,
            template_id=request.template_id,
            template_name=request.template_name,
            file_path=request.file_path,
            sections=request.sections,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load report content: {e}"
        )
