"""Gitleaks secrets detection analyzer."""

from analyzers.base_analyzer import BaseAnalyzer
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GitleaksAnalyzer(BaseAnalyzer):
    """
    Gitleaks secrets detection analyzer.
    
    Scans Git repositories for hard-coded secrets, API keys, tokens, etc.
    """
    
    name = "gitleaks-secrets"
    description = "Git repository secret scanning with Gitleaks"
    version = "1.0.0"
    supported_observable_types = ["git_repository"]
    tags = ["secret_scan", "devsec", "critical"]
    
    timeout_seconds = 180  # 3 minutes
    requires_credentials = False
    parallel_safe = True
    
    async def analyze(
        self,
        observable: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run Gitleaks scan on repository.
        
        Args:
            observable: Observable with repo URL
            config: Optional config with:
                - scan_depth: Git clone depth
        
        Returns:
            Analysis results with findings
        """
        repo_url = observable["value"]
        config = config or {}
        
        self.logger.info(f"Running Gitleaks scan on repository: {repo_url}")
        
        try:
            from tools.gitleaks import gitleaks_wrapper
            
            scan_depth = config.get("scan_depth", 1)
            
            results = await gitleaks_wrapper.scan_repository(
                repo_url=repo_url,
                scan_depth=scan_depth
            )
            
            # Parse findings
            findings = []
            for secret in results.get("findings", []):
                finding = self._parse_gitleaks_secret(secret, repo_url)
                findings.append(finding)
            
            return {
                "status": "success",
                "findings": findings,
                "metadata": {
                    "repo_url": repo_url,
                    "total_secrets": results.get("total_secrets", 0),
                    "gitleaks_version": results.get("gitleaks_version", "unknown")
                }
            }
        
        except Exception as e:
            self.logger.error(f"Gitleaks analysis failed: {str(e)}", exc_info=True)
            return {
                "status": "failure",
                "findings": [],
                "metadata": {},
                "error": str(e)
            }
    
    def _parse_gitleaks_secret(
        self,
        secret: Dict[str, Any],
        repo_url: str
    ) -> Dict[str, Any]:
        """
        Parse Gitleaks finding into finding format.
        
        Args:
            secret: Gitleaks secret finding
            repo_url: Repository URL
        
        Returns:
            Finding dictionary
        """
        # Gitleaks findings are always critical (exposed secrets)
        severity = "critical"
        
        rule_id = secret.get("RuleID", "")
        description = secret.get("Description", f"Secret detected: {rule_id}")
        
        return {
            "source": "secret_scan",
            "tool": "gitleaks",
            "check_id": rule_id,
            "title": f"Secret exposed: {rule_id}",
            "description": description,
            "severity": severity,
            "evidence": {
                "file": secret.get("File", ""),
                "line_number": secret.get("StartLine", 0),
                "commit": secret.get("Commit", ""),
                "author": secret.get("Author", ""),
                "email": secret.get("Email", ""),
                "date": secret.get("Date", ""),
                "secret_type": secret.get("RuleID", ""),
                "repo_url": repo_url,
                "match": secret.get("Match", "")[:50] + "..." if len(secret.get("Match", "")) > 50 else secret.get("Match", "")
            },
            "remediation": "Rotate the exposed secret immediately and remove from Git history using tools like BFG Repo-Cleaner or git-filter-repo",
            "framework_refs": {}
        }
    
    def get_priority(self, observable: Dict[str, Any]) -> int:
        """
        Secrets are always high priority.
        
        Args:
            observable: Observable dictionary
        
        Returns:
            Priority (always high for secrets)
        """
        return 20  # Secrets are critical
    
    def estimate_duration(self, observable: Dict[str, Any]) -> int:
        """
        Estimate duration based on repo size.
        
        Shallow clones are fast.
        """
        metadata = observable.get("metadata", {})
        scan_depth = metadata.get("scan_depth", 1)
        
        if scan_depth == 1:
            return 60  # 1 minute for shallow clone
        else:
            return 180  # 3 minutes for full history

