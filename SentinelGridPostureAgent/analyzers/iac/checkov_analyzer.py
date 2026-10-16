"""Checkov IaC security scanner analyzer."""

from analyzers.base_analyzer import BaseAnalyzer
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CheckovAnalyzer(BaseAnalyzer):
    """
    Checkov Infrastructure as Code security scanner.
    
    Scans Terraform, CloudFormation, Kubernetes manifests, etc. for misconfigurations.
    """
    
    name = "checkov-iac"
    description = "Infrastructure as Code security scanning with Checkov"
    version = "1.0.0"
    supported_observable_types = ["git_repository"]
    tags = ["iac", "sast", "critical"]
    
    timeout_seconds = 300  # 5 minutes
    requires_credentials = False
    parallel_safe = True
    
    def should_run(self, observable: Dict[str, Any]) -> bool:
        """
        Only run Checkov if repository contains IaC files.
        
        Args:
            observable: Observable dictionary
        
        Returns:
            True if repo has IaC files
        """
        if observable.get("type") != "git_repository":
            return False
        
        metadata = observable.get("metadata", {})
        has_iac = (
            metadata.get("has_terraform", False) or
            metadata.get("has_cloudformation", False) or
            metadata.get("has_kubernetes_manifests", False)
        )
        
        return has_iac
    
    async def analyze(
        self,
        observable: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run Checkov scan on repository.
        
        Args:
            observable: Observable with repo URL
            config: Optional config with:
                - frameworks: List of frameworks to check
                - checks: Specific checks to run
        
        Returns:
            Analysis results with findings
        """
        repo_url = observable["value"]
        config = config or {}
        
        self.logger.info(f"Running Checkov scan on repository: {repo_url}")
        
        try:
            from tools.checkov import checkov_wrapper
            
            frameworks = config.get("frameworks")
            checks = config.get("checks")
            
            results = await checkov_wrapper.scan_repository(
                repo_url=repo_url,
                frameworks=frameworks,
                checks=checks
            )
            
            # Parse findings (only failed checks)
            findings = []
            for check in results.get("failed_checks", []):
                finding = self._parse_checkov_check(check, repo_url)
                findings.append(finding)
            
            return {
                "status": "success",
                "findings": findings,
                "metadata": {
                    "repo_url": repo_url,
                    "files_scanned": results.get("summary", {}).get("files_scanned", 0),
                    "checks_run": results.get("summary", {}).get("passed", 0) + results.get("summary", {}).get("failed", 0),
                    "checkov_version": results.get("checkov_version", "unknown")
                }
            }
        
        except Exception as e:
            self.logger.error(f"Checkov analysis failed: {str(e)}", exc_info=True)
            return {
                "status": "failure",
                "findings": [],
                "metadata": {},
                "error": str(e)
            }
    
    def _parse_checkov_check(
        self,
        check: Dict[str, Any],
        repo_url: str
    ) -> Dict[str, Any]:
        """
        Parse Checkov check result into finding format.
        
        Args:
            check: Checkov check result
            repo_url: Repository URL
        
        Returns:
            Finding dictionary
        """
        # Map Checkov severity
        # Checkov doesn't always provide severity, infer from check type
        check_id = check.get("check_id", "")
        
        # Default severity based on check type patterns
        severity = "medium"
        if any(keyword in check_id.lower() for keyword in ["public", "unencrypted", "admin", "wildcard"]):
            severity = "high"
        if any(keyword in check_id.lower() for keyword in ["internet", "0.0.0.0", "credentials"]):
            severity = "critical"
        
        # Framework refs
        framework_refs = {}
        compliance = check.get("guideline", "")
        if "CIS" in compliance:
            framework_refs["cis"] = ["extracted_from_guideline"]
        
        return {
            "source": "iac",
            "tool": "checkov",
            "check_id": check_id,
            "title": check.get("check_name", "IaC misconfiguration"),
            "description": check.get("guideline", ""),
            "severity": severity,
            "evidence": {
                "file_path": check.get("file_path", ""),
                "file_line_range": check.get("file_line_range", []),
                "resource": check.get("resource", ""),
                "check_class": check.get("check_class", ""),
                "repo_url": repo_url
            },
            "remediation": check.get("guideline", ""),
            "framework_refs": framework_refs
        }
    
    def get_priority(self, observable: Dict[str, Any]) -> int:
        """Higher priority for repos with many IaC files."""
        metadata = observable.get("metadata", {})
        
        # Count IaC types
        iac_count = 0
        if metadata.get("has_terraform"):
            iac_count += 1
        if metadata.get("has_cloudformation"):
            iac_count += 1
        if metadata.get("has_kubernetes_manifests"):
            iac_count += 1
        
        return 5 + (iac_count * 3)  # More IaC = higher priority

