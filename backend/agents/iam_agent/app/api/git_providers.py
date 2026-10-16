"""
Git Provider Integration API

Provides endpoints for connecting and managing Git provider integrations.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import json
import uuid
from datetime import datetime
import httpx

from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.orm import Session, sessionmaker

from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_tenant_session,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def _github_health(token: str, org: Optional[str] = None) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    url = "https://api.github.com/user/repos"
    if org:
        url = f"https://api.github.com/orgs/{org}/repos"
    try:
        resp = httpx.get(url, headers=headers, timeout=5.0)
        ok = resp.status_code == 200
        data = resp.json() if ok else {}
        count = len(data) if isinstance(data, list) else None
        return {"success": ok, "message": f"GitHub reachable ({resp.status_code})", "repo_count": count}
    except Exception as e:
        return {"success": False, "message": "GitHub health failed", "error": str(e)}


def _gitlab_health(token: str, base_url: str, group: Optional[str] = None) -> Dict[str, Any]:
    headers = {"PRIVATE-TOKEN": token}
    url = f"{base_url.rstrip('/')}/api/v4/projects"
    params = {"membership": True}
    if group:
        url = f"{base_url.rstrip('/')}/api/v4/groups/{group}/projects"
        params = {}
    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=5.0)
        ok = resp.status_code == 200
        data = resp.json() if ok else {}
        count = len(data) if isinstance(data, list) else None
        return {"success": ok, "message": f"GitLab reachable ({resp.status_code})", "repo_count": count}
    except Exception as e:
        return {"success": False, "message": "GitLab health failed", "error": str(e)}


def _bitbucket_health(username: str, app_password: str, workspace: Optional[str]) -> Dict[str, Any]:
    auth = (username, app_password)
    url = f"https://api.bitbucket.org/2.0/repositories"
    if workspace:
        url = f"https://api.bitbucket.org/2.0/repositories/{workspace}"
    try:
        resp = httpx.get(url, auth=auth, timeout=5.0)
        ok = resp.status_code == 200
        data = resp.json() if ok else {}
        count = data.get("size") if isinstance(data, dict) else None
        return {"success": ok, "message": f"Bitbucket reachable ({resp.status_code})", "repo_count": count}
    except Exception as e:
        return {"success": False, "message": "Bitbucket health failed", "error": str(e)}


def _azure_devops_health(org: str, pat: str, project: Optional[str]) -> Dict[str, Any]:
    import base64
    token = base64.b64encode(f":{pat}".encode()).decode()
    headers = {"Authorization": f"Basic {token}"}
    base = f"https://dev.azure.com/{org}"
    url = f"{base}/_apis/projects?api-version=7.0"
    if project:
        url = f"{base}/{project}/_apis/git/repositories?api-version=7.0"
    try:
        resp = httpx.get(url, headers=headers, timeout=5.0)
        ok = resp.status_code == 200
        data = resp.json() if ok else {}
        count = data.get("count")
        return {"success": ok, "message": f"Azure DevOps reachable ({resp.status_code})", "repo_count": count}
    except Exception as e:
        return {"success": False, "message": "Azure DevOps health failed", "error": str(e)}

router = APIRouter(prefix="/api/v1/git-providers", tags=["git-providers"])

# ============================================================================
# Request/Response Models
# ============================================================================

class GitProviderConnectRequest(BaseModel):
    """Request to connect a Git provider."""
    provider: str  # github, gitlab, bitbucket, azure_devops, self_hosted
    config: Dict[str, Any]  # Provider-specific configuration
    organization: Optional[str] = None  # For GitHub/GitLab organizations
    workspace: Optional[str] = None  # For Bitbucket workspaces
    project: Optional[str] = None  # For Azure DevOps projects


class GitProviderResponse(BaseModel):
    """Response for Git provider connection."""
    id: str
    provider: str
    organization: Optional[str] = None
    workspace: Optional[str] = None
    project: Optional[str] = None
    status: str
    connected_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    repository_count: Optional[int] = None
    test_result: Optional[Dict[str, Any]] = None
    health: Optional[Dict[str, Any]] = None


class GitRepositoryResponse(BaseModel):
    """Response for Git repository information."""
    id: str
    provider_id: str
    name: str
    full_name: str
    url: str
    default_branch: str
    is_private: bool
    language: Optional[str] = None
    last_commit_at: Optional[datetime] = None
    scan_status: str
    findings_count: Optional[int] = None


def _current_customer_id(request_context: RequestContext) -> str:
    return str(request_context.tenant_id)


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/connect", response_model=GitProviderResponse)
async def connect_git_provider(
    request_data: GitProviderConnectRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    Connect a Git provider (GitHub, GitLab, Bitbucket, Azure DevOps).
    """
    try:
        customer_id = _current_customer_id(request_context)
        
        # Validate provider
        valid_providers = ["github", "gitlab", "bitbucket", "azure_devops", "self_hosted"]
        if request_data.provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        
        # Test connection based on provider
        test_result = None
        health = None
        try:
            # Import clients (would need to be in same package or adjust paths)
            # For now, we'll do basic validation
            if request_data.provider == "github":
                if not request_data.config.get("access_token"):
                    raise HTTPException(status_code=400, detail="GitHub access_token is required")
                test_result = _github_health(request_data.config.get("access_token"), request_data.organization)
                health = test_result
            elif request_data.provider == "gitlab":
                if not request_data.config.get("access_token"):
                    raise HTTPException(status_code=400, detail="GitLab access_token is required")
                test_result = _gitlab_health(request_data.config.get("access_token"), request_data.config.get("gitlab_url", "https://gitlab.com"), request_data.organization)
                health = test_result
            elif request_data.provider == "bitbucket":
                if not request_data.config.get("username") or not request_data.config.get("app_password"):
                    raise HTTPException(status_code=400, detail="Bitbucket username and app_password are required")
                test_result = _bitbucket_health(request_data.config.get("username"), request_data.config.get("app_password"), request_data.workspace)
                health = test_result
            elif request_data.provider == "azure_devops":
                if not request_data.config.get("organization") or not request_data.config.get("personal_access_token"):
                    raise HTTPException(status_code=400, detail="Azure DevOps organization and personal_access_token are required")
                test_result = _azure_devops_health(request_data.config.get("organization"), request_data.config.get("personal_access_token"), request_data.project)
                health = test_result
            else:
                # self_hosted - would need custom implementation
                test_result = {"success": True, "message": "Self-hosted Git connection"}
                health = test_result
            
            if not test_result.get("success"):
                logger.warning(f"Git provider connection test failed: {test_result.get('error')}")
                # Allow saving even if test fails (user can fix later)
        except Exception as e:
            logger.error(f"Error testing Git provider connection: {e}", exc_info=True)
            test_result = {
                "success": False,
                "error": str(e)
            }
        
        # Encrypt sensitive config (access tokens, passwords, etc.)
        # For now, store as-is (should encrypt in production)
        encrypted_config = json.dumps(request_data.config)
        
        # Generate provider ID
        provider_id = str(uuid.uuid4())
        
        # Store in database using legacy schema (provider, organization_name, metadata)
        if db:
            access_token = (
                request_data.config.get("access_token")
                or request_data.config.get("personal_access_token")
                or request_data.config.get("app_password")
                or ""
            )

            stmt = text("""
                INSERT INTO customer_git_providers (
                    id,
                    customer_id,
                    provider,
                    organization_name,
                    access_token_encrypted,
                    status,
                    connected_at,
                    metadata
                ) VALUES (
                    :id,
                    :customer_id,
                    :provider,
                    :organization_name,
                    :access_token_encrypted,
                    'connected',
                    NOW(),
                    CAST(:metadata AS jsonb)
                )
                ON CONFLICT (customer_id, provider, organization_name)
                DO UPDATE SET
                    access_token_encrypted = EXCLUDED.access_token_encrypted,
                    status = 'connected',
                    connected_at = NOW(),
                    updated_at = NOW(),
                    metadata = EXCLUDED.metadata
                RETURNING id
            """).bindparams(
                bindparam("metadata")
            )

            result = db.execute(
                stmt,
                {
                    "id": provider_id,
                    "customer_id": customer_id,
                    "provider": request_data.provider,
                    "organization_name": request_data.organization,
                    "access_token_encrypted": access_token,
                    "metadata": json.dumps({"config": request_data.config, "test_result": test_result, "health": health})
                }
            )
            row = result.fetchone()
            if row:
                provider_id = str(row[0])
            db.commit()
        else:
            # Mock for development
            provider_id = str(uuid.uuid4())
        
        logger.info(f"Git provider connected: {request_data.provider} for customer {customer_id}")

        # Mark onboarding progress for git
        if db:
            progress_id = customer_id
            try:
                from app.api.onboarding import _resolve_progress_key  # lazy import to avoid circular deps
                progress_id = _resolve_progress_key(customer_id, db)
            except Exception:
                pass
            db.execute(
                text("""
                    INSERT INTO onboarding_progress (customer_id, step_git_completed, step_git_completed_at)
                    VALUES (:customer_id, true, NOW())
                    ON CONFLICT (customer_id)
                    DO UPDATE SET
                        step_git_completed = true,
                        step_git_completed_at = NOW(),
                        updated_at = NOW()
                """),
                {"customer_id": progress_id}
            )
            db.commit()
        
        return GitProviderResponse(
            id=provider_id,
            provider=request_data.provider,
            organization=request_data.organization,
            workspace=request_data.workspace,
            project=request_data.project,
            status="connected",
            connected_at=datetime.now(),
            test_result=test_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting Git provider: {e}", exc_info=True)
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to connect Git provider: {str(e)}")


@router.get("", response_model=List[GitProviderResponse])
async def list_git_providers(
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """List all connected Git providers for the customer."""
    try:
        customer_id = _current_customer_id(request_context)
        
        if db:
            result = db.execute(
                text("""
                    SELECT 
                        id, provider, organization_name, status, connected_at, last_sync_at, metadata
                    FROM customer_git_providers
                    WHERE customer_id = :customer_id
                    ORDER BY connected_at DESC
                """),
                {"customer_id": customer_id}
            )
            rows = result.fetchall()
            
            providers = []
            for row in rows:
                metadata = json.loads(row[6]) if row[6] else {}
                providers.append(GitProviderResponse(
                    id=str(row[0]),
                    provider=row[1],
                    organization=row[2],
                    workspace=None,
                    project=None,
                    status=row[3],
                    connected_at=row[4],
                    last_sync_at=row[5],
                    repository_count=None,  # Would query from git_repositories table
                    test_result=metadata.get("test_result"),
                    health=metadata.get("health")
                ))
            
            return providers
        else:
            # Mock data for development
            return [
                GitProviderResponse(
                    id="1",
                    provider="github",
                    organization="example-org",
                    status="connected",
                    connected_at=datetime.now()
                )
            ]
        
    except Exception as e:
        logger.error(f"Error listing Git providers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list Git providers: {str(e)}")


@router.post("/recheck", response_model=GitProviderResponse)
async def recheck_git_provider(
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    Re-run a lightweight health check for the most recent git provider connection (placeholder).
    TODO: implement real list-repos call per provider.
    """
    try:
        customer_id = _current_customer_id(request_context)
        if not db:
            raise HTTPException(status_code=500, detail="Database not configured")
        row = db.execute(
            text("""
                SELECT id, provider, organization_name, metadata, connected_at
                FROM customer_git_providers
                WHERE customer_id = :customer_id
                ORDER BY connected_at DESC
                LIMIT 1
            """),
            {"customer_id": customer_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No git provider found")
        provider_id, provider_type, org, metadata, connected_at = row
        health = {"success": True, "message": "Health check placeholder (implement list repos)."}
        db.execute(
            text("""
                UPDATE customer_git_providers
                SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{health}', :health::jsonb, true),
                    updated_at = NOW()
                WHERE id = :id
            """),
            {"id": provider_id, "health": json.dumps(health)}
        )
        db.commit()
        meta_obj = metadata or {}
        return GitProviderResponse(
            id=str(provider_id),
            provider=provider_type,
            organization=org,
            workspace=None,
            project=None,
            status="connected",
            connected_at=connected_at or datetime.now(),
            health=health,
            test_result=meta_obj.get("test_result") if isinstance(meta_obj, dict) else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rechecking git provider health: {e}", exc_info=True)
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to recheck git provider: {str(e)}")


@router.get("/{provider_id}/repositories", response_model=List[GitRepositoryResponse])
async def list_repositories(
    provider_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """List repositories for a connected Git provider."""
    try:
        customer_id = _current_customer_id(request_context)
        
        if db:
            # Get provider config
            provider_result = db.execute(
                text("""
                    SELECT provider, organization_name, metadata
                    FROM customer_git_providers
                    WHERE id = :provider_id AND customer_id = :customer_id
                """),
                {"provider_id": provider_id, "customer_id": customer_id}
            )
            provider_row = provider_result.fetchone()
            
            if not provider_row:
                raise HTTPException(status_code=404, detail="Git provider not found")
            
            provider_type = provider_row[0]
            metadata = provider_row[2] or {}
            organization = provider_row[1]
            workspace = None
            project = None
            
            # Query repositories from database
            repo_result = db.execute(
                text("""
                    SELECT 
                        id, name, full_name, url, default_branch, is_private,
                        language, last_commit_at, scan_status
                    FROM git_repositories
                    WHERE git_provider_id = :provider_id
                    ORDER BY name
                """),
                {"provider_id": provider_id}
            )
            repo_rows = repo_result.fetchall()
            
            repositories = []
            for row in repo_rows:
                # Count findings
                findings_result = db.execute(
                    text("""
                        SELECT COUNT(*) FROM git_security_findings
                        WHERE repo_id = :repo_id AND status = 'open'
                    """),
                    {"repo_id": row[0]}
                )
                findings_count = findings_result.fetchone()[0] if findings_result else 0
                
                repositories.append(GitRepositoryResponse(
                    id=str(row[0]),
                    provider_id=provider_id,
                    name=row[1],
                    full_name=row[2],
                    url=row[3],
                    default_branch=row[4],
                    is_private=row[5],
                    language=row[6],
                    last_commit_at=row[7],
                    scan_status=row[8],
                    findings_count=findings_count
                ))
            
            return repositories
        else:
            # Mock data for development
            return [
                GitRepositoryResponse(
                    id="1",
                    provider_id=provider_id,
                    name="example-repo",
                    full_name="example-org/example-repo",
                    url="https://github.com/example-org/example-repo",
                    default_branch="main",
                    is_private=True,
                    language="Python",
                    scan_status="pending"
                )
            ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing repositories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")


@router.post("/{provider_id}/sync")
async def sync_repositories(
    provider_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    Sync repositories from Git provider.
    This will fetch the latest repository list and update the database.
    """
    try:
        customer_id = _current_customer_id(request_context)
        
        # Get provider config
        if db:
            provider_result = db.execute(
                text("""
                    SELECT provider, organization_name, metadata
                    FROM customer_git_providers
                    WHERE id = :provider_id AND customer_id = :customer_id
                """),
                {"provider_id": provider_id, "customer_id": customer_id}
            )
            provider_row = provider_result.fetchone()
            
            if not provider_row:
                raise HTTPException(status_code=404, detail="Git provider not found")
            
            provider_type = provider_row[0]
            organization = provider_row[1]
            meta_obj = provider_row[2] or {}
            config = meta_obj.get("config") if isinstance(meta_obj, dict) else {}
            workspace = None
            project = None
            
            # Fetch repositories from provider API
            # TODO: Implement actual API calls using git provider clients
            # For now, return empty list (would be implemented with actual clients)
            repositories = []
            
            # Example structure for GitHub:
            # if provider_type == "github":
            #     from backend.services.git_security.github.github_client import GitHubClient
            #     client = GitHubClient(config.get("access_token", ""))
            #     repos = await client.list_repositories(organization)
            #     for repo in repos:
            #         repositories.append({
            #             "name": repo.get("name"),
            #             "full_name": repo.get("full_name"),
            #             "url": repo.get("html_url"),
            #             "default_branch": repo.get("default_branch", "main"),
            #             "is_private": repo.get("private", False),
            #             "language": repo.get("language"),
            #             "external_id": str(repo.get("id"))
            #         })
            
            # Store repositories in database
            for repo in repositories:
                db.execute(
                    text("""
                        INSERT INTO git_repositories (
                            id, customer_id, git_provider_id, name, full_name,
                            url, default_branch, is_private, language, external_id,
                            scan_status, discovered_at
                        ) VALUES (
                            gen_random_uuid(), :customer_id, :provider_id, :name, :full_name,
                            :url, :default_branch, :is_private, :language, :external_id,
                            'pending', NOW()
                        )
                        ON CONFLICT (git_provider_id, external_id)
                        DO UPDATE SET
                            name = EXCLUDED.name,
                            full_name = EXCLUDED.full_name,
                            url = EXCLUDED.url,
                            default_branch = EXCLUDED.default_branch,
                            is_private = EXCLUDED.is_private,
                            language = EXCLUDED.language,
                            updated_at = NOW()
                    """),
                    {
                        "customer_id": customer_id,
                        "provider_id": provider_id,
                        **repo
                    }
                )
            
            # Update last_sync_at
            db.execute(
                text("""
                    UPDATE customer_git_providers
                    SET last_sync_at = NOW(), updated_at = NOW()
                    WHERE id = :provider_id
                """),
                {"provider_id": provider_id}
            )
            
            db.commit()
            
            return {
                "success": True,
                "repositories_synced": len(repositories),
                "message": f"Synced {len(repositories)} repositories"
            }
        else:
            return {
                "success": True,
                "repositories_synced": 0,
                "message": "Database not configured"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing repositories: {e}", exc_info=True)
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync repositories: {str(e)}")
