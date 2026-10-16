"""
Git Security Scanning API

Provides endpoints for scanning Git repositories and retrieving security findings.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
import json
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_tenant_session,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/git-scanning", tags=["git-scanning"])

# ============================================================================
# Request/Response Models
# ============================================================================

class ScanRequest(BaseModel):
    """Request to scan a repository."""
    repo_id: str
    scan_types: List[str] = ["secrets", "dependencies", "code"]  # secrets, dependencies, code
    branch: Optional[str] = None  # Default to repository default branch


class ScanResponse(BaseModel):
    """Response for scan operation."""
    scan_id: str
    repo_id: str
    status: str  # queued, running, completed, failed
    scan_types: List[str]
    findings_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class FindingResponse(BaseModel):
    """Response for a security finding."""
    id: str
    repo_id: str
    finding_type: str  # secret, vulnerability, code_issue, dependency_vulnerability
    severity: str  # critical, high, medium, low, info
    title: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    commit_sha: Optional[str] = None
    scanner_tool: str
    scanner_rule_id: Optional[str] = None
    status: str  # open, resolved, false_positive, ignored
    detected_at: datetime


class FindingListResponse(BaseModel):
    """Response for listing findings."""
    findings: List[FindingResponse]
    total: int
    page: int
    page_size: int


def _current_customer_id(request_context: RequestContext) -> str:
    return str(request_context.tenant_id)


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/scan", response_model=ScanResponse)
async def scan_repository(
    request_data: ScanRequest,
    background_tasks: BackgroundTasks,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    Trigger a security scan for a repository.
    """
    try:
        customer_id = _current_customer_id(request_context)
        
        # Get repository info
        if db:
            repo_result = db.execute(
                text("""
                    SELECT id, name, full_name, url, default_branch, git_provider_id
                    FROM git_repositories
                    WHERE id = :repo_id AND customer_id = :customer_id
                """),
                {"repo_id": request_data.repo_id, "customer_id": customer_id}
            )
            repo_row = repo_result.fetchone()
            
            if not repo_row:
                raise HTTPException(status_code=404, detail="Repository not found")
            
            repo_id, repo_name, full_name, url, default_branch, provider_id = repo_row
            scan_branch = request_data.branch or default_branch or "main"
        else:
            # Mock for development
            repo_id = request_data.repo_id
            repo_name = "example-repo"
            full_name = "example-org/example-repo"
            url = "https://github.com/example-org/example-repo"
            scan_branch = request_data.branch or "main"
            provider_id = "1"
        
        # Generate scan ID
        scan_id = str(uuid.uuid4())
        
        # Store scan job
        if db:
            db.execute(
                text("""
                    INSERT INTO git_security_scans (
                        id, customer_id, repo_id, scan_types, branch, status, started_at
                    ) VALUES (
                        :id, :customer_id, :repo_id, :scan_types::jsonb, :branch, 'queued', NOW()
                    )
                """),
                {
                    "id": scan_id,
                    "customer_id": customer_id,
                    "repo_id": repo_id,
                    "scan_types": json.dumps(request_data.scan_types),
                    "branch": scan_branch
                }
            )
            db.commit()
        
        # Queue background scan task
        background_tasks.add_task(
            perform_scan,
            scan_id=scan_id,
            repo_id=repo_id,
            repo_name=repo_name,
            full_name=full_name,
            url=url,
            branch=scan_branch,
            scan_types=request_data.scan_types,
            provider_id=provider_id,
            customer_id=customer_id
        )
        
        logger.info(f"Queued scan {scan_id} for repository {repo_id}")
        
        return ScanResponse(
            scan_id=scan_id,
            repo_id=repo_id,
            status="queued",
            scan_types=request_data.scan_types,
            started_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing scan: {e}", exc_info=True)
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to queue scan: {str(e)}")


async def perform_scan(
    scan_id: str,
    repo_id: str,
    repo_name: str,
    full_name: str,
    url: str,
    branch: str,
    scan_types: List[str],
    provider_id: str,
    customer_id: str
):
    """
    Perform the actual security scan (runs in background).
    """
    try:
        logger.info(f"Starting scan {scan_id} for repository {repo_id}")
        
        # Update scan status to running
        if settings.DB_URL:
            engine = create_engine(settings.DB_URL)
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        UPDATE git_security_scans
                        SET status = 'running', started_at = NOW()
                        WHERE id = :scan_id
                    """),
                    {"scan_id": scan_id}
                )
                conn.commit()
        
        findings = []
        
        # Clone repository to temp directory
        import tempfile
        import shutil
        import git
        
        temp_dir = tempfile.mkdtemp()
        try:
            # Clone repository
            repo = git.Repo.clone_from(url, temp_dir, branch=branch, depth=1)
            
            # Run scans based on scan_types
            if "secrets" in scan_types:
                from backend.services.git_security.scanners.gitleaks.gitleaks_scanner import GitleaksScanner
                scanner = GitleaksScanner()
                gitleaks_findings = scanner.scan_repository(temp_dir, branch=branch)
                for finding in gitleaks_findings:
                    normalized = scanner.normalize_finding(finding)
                    normalized["repo_id"] = repo_id
                    findings.append(normalized)
            
            if "dependencies" in scan_types:
                from backend.services.git_security.scanners.trivy.trivy_scanner import TrivyScanner
                scanner = TrivyScanner()
                trivy_result = scanner.scan_repository(temp_dir, scan_type="fs")
                trivy_findings = scanner.extract_vulnerabilities(trivy_result)
                for finding in trivy_findings:
                    finding["repo_id"] = repo_id
                    findings.append(finding)
            
            if "code" in scan_types:
                from backend.services.git_security.scanners.semgrep.semgrep_scanner import SemgrepScanner
                scanner = SemgrepScanner()
                semgrep_result = scanner.scan_repository(temp_dir, config="p/security-audit")
                semgrep_findings = scanner.extract_findings(semgrep_result)
                for finding in semgrep_findings:
                    finding["repo_id"] = repo_id
                    findings.append(finding)
            
            # Store findings in database
            if settings.DB_URL and findings:
                engine = create_engine(settings.DB_URL)
                with engine.connect() as conn:
                    for finding in findings:
                        conn.execute(
                            text("""
                                INSERT INTO git_security_findings (
                                    id, customer_id, repo_id, finding_type, severity,
                                    title, description, file_path, line_number, commit_sha,
                                    scanner_tool, scanner_rule_id, status, detected_at
                                ) VALUES (
                                    gen_random_uuid(), :customer_id, :repo_id, :finding_type, :severity,
                                    :title, :description, :file_path, :line_number, :commit_sha,
                                    :scanner_tool, :scanner_rule_id, 'open', NOW()
                                )
                                ON CONFLICT (repo_id, scanner_tool, scanner_rule_id, file_path, line_number)
                                DO UPDATE SET
                                    severity = EXCLUDED.severity,
                                    title = EXCLUDED.title,
                                    description = EXCLUDED.description,
                                    detected_at = EXCLUDED.detected_at,
                                    updated_at = NOW()
                            """),
                            {
                                "customer_id": customer_id,
                                "repo_id": repo_id,
                                "finding_type": finding.get("finding_type"),
                                "severity": finding.get("severity"),
                                "title": finding.get("title"),
                                "description": finding.get("description"),
                                "file_path": finding.get("file_path"),
                                "line_number": finding.get("line_number"),
                                "commit_sha": finding.get("commit_sha"),
                                "scanner_tool": finding.get("scanner_tool"),
                                "scanner_rule_id": finding.get("scanner_rule_id")
                            }
                        )
                    conn.commit()
            
            # Update scan status to completed
            if settings.DB_URL:
                engine = create_engine(settings.DB_URL)
                with engine.connect() as conn:
                    conn.execute(
                        text("""
                            UPDATE git_security_scans
                            SET status = 'completed', completed_at = NOW(), findings_count = :count
                            WHERE id = :scan_id
                        """),
                        {"scan_id": scan_id, "count": len(findings)}
                    )
                    conn.commit()
            
            logger.info(f"Scan {scan_id} completed with {len(findings)} findings")
            
        finally:
            # Cleanup temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
    except Exception as e:
        logger.error(f"Error performing scan {scan_id}: {e}", exc_info=True)
        
        # Update scan status to failed
        if settings.DB_URL:
            engine = create_engine(settings.DB_URL)
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        UPDATE git_security_scans
                        SET status = 'failed', completed_at = NOW(), error = :error
                        WHERE id = :scan_id
                    """),
                    {"scan_id": scan_id, "error": str(e)}
                )
                conn.commit()


@router.get("/findings", response_model=FindingListResponse)
async def list_findings(
    repo_id: Optional[str] = None,
    finding_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = "open",
    page: int = 1,
    page_size: int = 20,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    List security findings with filtering and pagination.
    """
    try:
        customer_id = _current_customer_id(request_context)
        
        # Build WHERE clause
        where_conditions = ["customer_id = :customer_id"]
        params = {"customer_id": customer_id}
        
        if repo_id:
            where_conditions.append("repo_id = :repo_id")
            params["repo_id"] = repo_id
        
        if finding_type:
            where_conditions.append("finding_type = :finding_type")
            params["finding_type"] = finding_type
        
        if severity:
            where_conditions.append("severity = :severity")
            params["severity"] = severity
        
        if status:
            where_conditions.append("status = :status")
            params["status"] = status
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total
        if db:
            count_query = f"""
                SELECT COUNT(*) as total
                FROM git_security_findings
                WHERE {where_clause}
            """
            count_result = db.execute(text(count_query), params)
            total = count_result.fetchone()[0]
        else:
            total = 0
        
        # Get findings
        offset = (page - 1) * page_size
        query = f"""
            SELECT 
                id, repo_id, finding_type, severity, title, description,
                file_path, line_number, commit_sha, scanner_tool, scanner_rule_id,
                status, detected_at
            FROM git_security_findings
            WHERE {where_clause}
            ORDER BY 
                CASE severity
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                detected_at DESC
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = page_size
        params["offset"] = offset
        
        if db:
            result = db.execute(text(query), params)
            rows = result.fetchall()
            
            findings = []
            for row in rows:
                findings.append(FindingResponse(
                    id=str(row[0]),
                    repo_id=str(row[1]),
                    finding_type=row[2],
                    severity=row[3],
                    title=row[4],
                    description=row[5],
                    file_path=row[6],
                    line_number=row[7],
                    commit_sha=row[8],
                    scanner_tool=row[9],
                    scanner_rule_id=row[10],
                    status=row[11],
                    detected_at=row[12]
                ))
        else:
            # Mock data for development
            findings = []
        
        return FindingListResponse(
            findings=findings,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing findings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list findings: {str(e)}")


@router.get("/findings/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Get details for a specific finding."""
    try:
        customer_id = _current_customer_id(request_context)
        
        if db:
            result = db.execute(
                text("""
                    SELECT 
                        id, repo_id, finding_type, severity, title, description,
                        file_path, line_number, commit_sha, scanner_tool, scanner_rule_id,
                        status, detected_at
                    FROM git_security_findings
                    WHERE id = :finding_id AND customer_id = :customer_id
                """),
                {"finding_id": finding_id, "customer_id": customer_id}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Finding not found")
            
            return FindingResponse(
                id=str(row[0]),
                repo_id=str(row[1]),
                finding_type=row[2],
                severity=row[3],
                title=row[4],
                description=row[5],
                file_path=row[6],
                line_number=row[7],
                commit_sha=row[8],
                scanner_tool=row[9],
                scanner_rule_id=row[10],
                status=row[11],
                detected_at=row[12]
            )
        else:
            raise HTTPException(status_code=404, detail="Finding not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting finding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get finding: {str(e)}")


@router.patch("/findings/{finding_id}")
async def update_finding_status(
    finding_id: str,
    status: str,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Update finding status (resolve, mark as false positive, etc.)."""
    try:
        customer_id = _current_customer_id(request_context)
        
        valid_statuses = ["open", "resolved", "false_positive", "ignored"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        if db:
            result = db.execute(
                text("""
                    UPDATE git_security_findings
                    SET status = :status, updated_at = NOW()
                    WHERE id = :finding_id AND customer_id = :customer_id
                    RETURNING id
                """),
                {"finding_id": finding_id, "customer_id": customer_id, "status": status}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Finding not found")
            
            db.commit()
            
            return {"success": True, "status": status}
        else:
            return {"success": True, "status": status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating finding status: {e}", exc_info=True)
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update finding: {str(e)}")
