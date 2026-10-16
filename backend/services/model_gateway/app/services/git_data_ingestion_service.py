"""
Git Data Ingestion Service
Automated pipeline for ingesting knowledge base data from git repositories.

Supports:
- Customer-specific repos (tenant_id = customer UUID)
- Global/shared repos (tenant_id = NULL)
- Webhook-triggered ingestion
- Scheduled polling (fallback)
"""

import logging
import os
import json
import subprocess
import tempfile
import shutil
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from app.services.knowledge_base_loader import KnowledgeBaseLoader
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Try to use GitPython, fallback to subprocess
try:
    from git import Repo
    GITPYTHON_AVAILABLE = True
except ImportError:
    GITPYTHON_AVAILABLE = False
    logger.warning("GitPython not available. Using subprocess for git operations.")


class GitDataIngestionService:
    """Service for ingesting knowledge base data from git repositories."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
        self.knowledge_loader = KnowledgeBaseLoader(db_session=db_session)
        self.rag_service = RAGService(db_session=db_session)
        self.temp_dir = Path(os.getenv("GIT_TEMP_DIR", "/tmp/git_ingestion"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def ingest_from_repo(
        self,
        repo_url: str,
        repo_type: str = "customer",  # "customer" or "global"
        tenant_id: Optional[str] = None,
        branch: str = "main",
        paths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Clone repository and ingest knowledge base data.
        
        Args:
            repo_url: Git repository URL (HTTPS or SSH)
            repo_type: "customer" (tenant-specific) or "global" (shared)
            tenant_id: Tenant ID (required for customer repos)
            branch: Git branch to checkout
            paths: Optional list of paths to process (e.g., ["knowledge-base/", "data/"])
                   If None, processes common paths
            
        Returns:
            Ingestion result summary
        """
        if repo_type == "customer" and not tenant_id:
            return {
                "status": "error",
                "error": "tenant_id is required for customer repositories"
            }
        
        repo_id = self._get_repo_id(repo_url)
        clone_path = self.temp_dir / repo_id
        
        try:
            # Clone or update repository
            self._clone_or_update_repo(repo_url, clone_path, branch)
            
            # Discover knowledge base files
            kb_files = self._discover_kb_files(clone_path, paths)
            
            if not kb_files:
                return {
                    "status": "success",
                    "message": "No knowledge base files found",
                    "files_processed": 0
                }
            
            # Process each file
            results = {
                "nist": {"loaded": 0, "errors": 0},
                "mitre": {"loaded": 0, "errors": 0},
                "owasp": {"loaded": 0, "errors": 0},
                "playbooks": {"loaded": 0, "errors": 0},
                "custom": {"loaded": 0, "errors": 0}
            }
            
            for file_path in kb_files:
                file_result = self._process_file(file_path, repo_type, tenant_id)
                
                category = file_result.get("category", "custom")
                if file_result.get("status") == "success":
                    results[category]["loaded"] += file_result.get("loaded", 0)
                else:
                    results[category]["errors"] += 1
            
            total_loaded = sum(r["loaded"] for r in results.values())
            total_errors = sum(r["errors"] for r in results.values())
            
            return {
                "status": "success" if total_errors == 0 else "partial",
                "repo_url": repo_url,
                "repo_type": repo_type,
                "tenant_id": tenant_id,
                "files_processed": len(kb_files),
                "results": results,
                "total_loaded": total_loaded,
                "total_errors": total_errors,
                "ingested_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error ingesting from repo {repo_url}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "repo_url": repo_url
            }
        finally:
            # Cleanup (optional - could keep for caching)
            # shutil.rmtree(clone_path, ignore_errors=True)
            pass
    
    def _get_repo_id(self, repo_url: str) -> str:
        """Generate unique ID for repository."""
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        # Add hash of full URL for uniqueness
        import hashlib
        url_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
        return f"{repo_name}-{url_hash}"
    
    def _clone_or_update_repo(self, repo_url: str, clone_path: Path, branch: str):
        """Clone repository or update if exists."""
        if GITPYTHON_AVAILABLE:
            try:
                if clone_path.exists() and (clone_path / ".git").exists():
                    # Update existing clone
                    logger.info(f"Updating existing repository at {clone_path}")
                    repo = Repo(clone_path)
                    repo.remotes.origin.fetch()
                    repo.git.checkout(branch)
                    repo.remotes.origin.pull(branch)
                else:
                    # Clone new repository
                    logger.info(f"Cloning repository {repo_url} to {clone_path}")
                    clone_path.parent.mkdir(parents=True, exist_ok=True)
                    Repo.clone_from(repo_url, str(clone_path), branch=branch)
                return
            except Exception as e:
                logger.warning(f"GitPython failed, falling back to subprocess: {e}")
        
        # Fallback to subprocess
        if clone_path.exists() and (clone_path / ".git").exists():
            # Update existing clone
            logger.info(f"Updating existing repository at {clone_path}")
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=clone_path,
                check=True,
                capture_output=True,
                timeout=300
            )
            subprocess.run(
                ["git", "checkout", branch],
                cwd=clone_path,
                check=True,
                capture_output=True,
                timeout=60
            )
            subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=clone_path,
                check=True,
                capture_output=True,
                timeout=300
            )
        else:
            # Clone new repository
            logger.info(f"Cloning repository {repo_url} to {clone_path}")
            clone_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "-b", branch, repo_url, str(clone_path)],
                check=True,
                capture_output=True,
                timeout=600
            )
    
    def _discover_kb_files(self, repo_path: Path, paths: Optional[List[str]] = None) -> List[Path]:
        """Discover knowledge base files in repository."""
        kb_files = []
        
        # Default search paths
        search_paths = paths or [
            "knowledge-base/",
            "data/",
            "kb/",
            "frameworks/",
            ".",
        ]
        
        # File patterns to look for
        patterns = [
            "**/*nist*.json",
            "**/*mitre*.json",
            "**/*owasp*.json",
            "**/*playbook*.json",
            "**/knowledge*.json",
            "**/kb-*.json",
        ]
        
        for search_path in search_paths:
            search_dir = repo_path / search_path
            
            if not search_dir.exists():
                continue
            
            for pattern in patterns:
                kb_files.extend(search_dir.glob(pattern))
        
        # Also check for specific structure
        structured_paths = [
            repo_path / "nist" / "controls.json",
            repo_path / "mitre" / "techniques.json",
            repo_path / "owasp" / "content.json",
            repo_path / "playbooks" / "playbooks.json",
        ]
        
        kb_files.extend([p for p in structured_paths if p.exists()])
        
        # Remove duplicates
        return list(set(kb_files))
    
    def _process_file(self, file_path: Path, repo_type: str, tenant_id: Optional[str]) -> Dict[str, Any]:
        """Process a single knowledge base file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Detect category from file name or content
            category = self._detect_category(file_path, data)
            
            # Process based on category
            if category == "nist":
                result = self._process_nist_data(data, repo_type, tenant_id)
            elif category == "mitre":
                result = self._process_mitre_data(data, repo_type, tenant_id)
            elif category == "owasp":
                result = self._process_owasp_data(data, repo_type, tenant_id)
            elif category == "playbooks":
                result = self._process_playbooks_data(data, repo_type, tenant_id)
            else:
                result = self._process_custom_data(data, file_path, repo_type, tenant_id)
            
            result["category"] = category
            result["file"] = str(file_path)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return {"status": "error", "error": f"Invalid JSON: {e}"}
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return {"status": "error", "error": str(e)}
    
    def _detect_category(self, file_path: Path, data: Dict[str, Any]) -> str:
        """Detect knowledge base category from file or content."""
        file_str = str(file_path).lower()
        
        if "nist" in file_str or "control" in file_str:
            if "controls" in data or any("AC-" in str(item) for item in data.get("items", [])):
                return "nist"
        
        if "mitre" in file_str or "attack" in file_str or "technique" in file_str:
            if "techniques" in data or any("T" in str(item.get("id", "")) for item in data.get("items", [])):
                return "mitre"
        
        if "owasp" in file_str:
            if "items" in data or any("A" in str(item.get("id", "")) for item in data.get("items", [])):
                return "owasp"
        
        if "playbook" in file_str:
            if "playbooks" in data or "steps" in data:
                return "playbooks"
        
        return "custom"
    
    def _process_nist_data(self, data: Dict[str, Any], repo_type: str, tenant_id: Optional[str]) -> Dict[str, Any]:
        """Process NIST controls data."""
        # Use existing loader method
        # Need to adapt to handle tenant_id properly
        controls = data.get("controls", data.get("items", []))
        
        loaded = 0
        errors = 0
        
        for control in controls:
            try:
                content_parts = [control.get("description", "")]
                if control.get("guidance"):
                    content_parts.append(f"\n\nGuidance: {control.get('guidance')}")
                
                result = self.rag_service.store_knowledge(
                    category="nist",
                    title=control.get("id", control.get("name", "NIST Control")),
                    content="\n".join(content_parts),
                    tenant_id=tenant_id if repo_type == "customer" else None,
                    subcategory="control",
                    metadata={
                        "control_id": control.get("id"),
                        "control_family": control.get("family", ""),
                        "source_repo": True
                    },
                    framework_version=control.get("version", "800-53r5")
                )
                
                if result.get("status") == "success":
                    loaded += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error processing NIST control: {e}")
        
        return {"status": "success", "loaded": loaded, "errors": errors}
    
    def _process_mitre_data(self, data: Dict[str, Any], repo_type: str, tenant_id: Optional[str]) -> Dict[str, Any]:
        """Process MITRE ATT&CK techniques data."""
        techniques = data.get("techniques", data.get("items", []))
        
        loaded = 0
        errors = 0
        
        for technique in techniques:
            try:
                content_parts = [technique.get("description", "")]
                if technique.get("detection"):
                    content_parts.append(f"\n\nDetection: {technique.get('detection')}")
                if technique.get("mitigation"):
                    content_parts.append(f"\n\nMitigation: {technique.get('mitigation')}")
                
                result = self.rag_service.store_knowledge(
                    category="mitre",
                    title=technique.get("name", technique.get("id", "MITRE Technique")),
                    content="\n".join(content_parts),
                    tenant_id=tenant_id if repo_type == "customer" else None,
                    subcategory="technique",
                    metadata={
                        "technique_id": technique.get("id"),
                        "tactic": technique.get("tactic", []),
                        "source_repo": True
                    },
                    framework_version=technique.get("version", "ATT&CK v13")
                )
                
                if result.get("status") == "success":
                    loaded += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error processing MITRE technique: {e}")
        
        return {"status": "success", "loaded": loaded, "errors": errors}
    
    def _process_owasp_data(self, data: Dict[str, Any], repo_type: str, tenant_id: Optional[str]) -> Dict[str, Any]:
        """Process OWASP content data."""
        items = data.get("items", data.get("content", []))
        
        loaded = 0
        errors = 0
        
        for item in items:
            try:
                content_parts = [item.get("description", "")]
                if item.get("how_to_prevent"):
                    content_parts.append(f"\n\nHow to Prevent: {item.get('how_to_prevent')}")
                
                result = self.rag_service.store_knowledge(
                    category="owasp",
                    title=item.get("name", item.get("id", "OWASP Item")),
                    content="\n".join(content_parts),
                    tenant_id=tenant_id if repo_type == "customer" else None,
                    subcategory=item.get("type", "top10"),
                    metadata={
                        "item_id": item.get("id"),
                        "risk_rating": item.get("risk_rating", ""),
                        "source_repo": True
                    },
                    framework_version=item.get("version", "2021")
                )
                
                if result.get("status") == "success":
                    loaded += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error processing OWASP item: {e}")
        
        return {"status": "success", "loaded": loaded, "errors": errors}
    
    def _process_playbooks_data(self, data: Dict[str, Any], repo_type: str, tenant_id: Optional[str]) -> Dict[str, Any]:
        """Process SOC playbooks data."""
        playbooks = data.get("playbooks", data.get("items", []))
        
        loaded = 0
        errors = 0
        
        for playbook in playbooks:
            try:
                content_parts = [playbook.get("description", "")]
                if playbook.get("steps"):
                    content_parts.append("\n\nSteps:")
                    for step in playbook.get("steps", []):
                        content_parts.append(f"\n{step.get('name', '')}")
                        if step.get("description"):
                            content_parts.append(f"  {step.get('description')}")
                
                result = self.rag_service.store_knowledge(
                    category="playbook",
                    title=playbook.get("name", playbook.get("id", "SOC Playbook")),
                    content="\n".join(content_parts),
                    tenant_id=tenant_id if repo_type == "customer" else None,
                    subcategory="incident_response",
                    metadata={
                        "playbook_id": playbook.get("id"),
                        "mitre_tactics": playbook.get("mitre_tactics", []),
                        "source_repo": True
                    }
                )
                
                if result.get("status") == "success":
                    loaded += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error processing playbook: {e}")
        
        return {"status": "success", "loaded": loaded, "errors": errors}
    
    def _process_custom_data(self, data: Dict[str, Any], file_path: Path, repo_type: str, tenant_id: Optional[str]) -> Dict[str, Any]:
        """Process custom/unknown format data."""
        # Try to extract knowledge base entries from generic structure
        items = data.get("items", data.get("entries", [data]))
        
        loaded = 0
        errors = 0
        
        for item in items:
            try:
                # Generic processing - try to extract title and content
                title = item.get("title", item.get("name", item.get("id", "Unknown")))
                content = item.get("content", item.get("description", ""))
                
                if not content:
                    continue
                
                category = item.get("category", "custom")
                
                result = self.rag_service.store_knowledge(
                    category=category,
                    title=title,
                    content=content,
                    tenant_id=tenant_id if repo_type == "customer" else None,
                    metadata={
                        "source_file": str(file_path.name),
                        "source_repo": True
                    }
                )
                
                if result.get("status") == "success":
                    loaded += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error(f"Error processing custom item: {e}")
        
        return {"status": "success", "loaded": loaded, "errors": errors}
    
    def process_webhook_payload(
        self,
        webhook_data: Dict[str, Any],
        repo_type: str = "customer",
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process git webhook payload (GitHub, GitLab, etc.).
        
        Args:
            webhook_data: Webhook payload from git provider
            repo_type: "customer" or "global"
            tenant_id: Tenant ID for customer repos
            
        Returns:
            Ingestion result
        """
        try:
            # Extract repository information from webhook
            repo_info = self._extract_repo_info(webhook_data)
            
            if not repo_info:
                return {
                    "status": "error",
                    "error": "Could not extract repository information from webhook"
                }
            
            # Check if knowledge base files were modified
            changed_files = self._get_changed_files(webhook_data)
            kb_files_changed = [
                f for f in changed_files
                if any(pattern in f.lower() for pattern in ["nist", "mitre", "owasp", "playbook", "knowledge", "kb-"])
            ]
            
            if not kb_files_changed:
                return {
                    "status": "skipped",
                    "message": "No knowledge base files changed"
                }
            
            # Ingest from repository
            return self.ingest_from_repo(
                repo_url=repo_info["url"],
                repo_type=repo_type,
                tenant_id=tenant_id,
                branch=repo_info.get("branch", "main")
            )
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _extract_repo_info(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract repository information from webhook payload."""
        # GitHub format
        if "repository" in webhook_data:
            repo = webhook_data["repository"]
            return {
                "url": repo.get("clone_url") or repo.get("html_url"),
                "branch": webhook_data.get("ref", "refs/heads/main").replace("refs/heads/", "")
            }
        
        # GitLab format
        if "project" in webhook_data:
            project = webhook_data["project"]
            return {
                "url": project.get("git_http_url") or project.get("web_url"),
                "branch": webhook_data.get("ref", "main")
            }
        
        # Generic format
        if "repo_url" in webhook_data:
            return {
                "url": webhook_data["repo_url"],
                "branch": webhook_data.get("branch", "main")
            }
        
        return None
    
    def _get_changed_files(self, webhook_data: Dict[str, Any]) -> List[str]:
        """Extract list of changed files from webhook."""
        files = []
        
        # GitHub push event
        if "commits" in webhook_data:
            for commit in webhook_data["commits"]:
                files.extend(commit.get("added", []))
                files.extend(commit.get("modified", []))
        
        # GitLab push event
        if "commits" in webhook_data:
            for commit in webhook_data.get("commits", []):
                files.extend(commit.get("added", []))
                files.extend(commit.get("modified", []))
        
        return list(set(files))

