"""Trivy vulnerability scanner analyzer for container images."""

from analyzers.base_analyzer import BaseAnalyzer
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TrivyAnalyzer(BaseAnalyzer):
    """
    Trivy vulnerability scanner for container images.
    
    Scans Docker images for known CVEs and vulnerabilities.
    """
    
    name = "trivy-vuln-scan"
    description = "Container image vulnerability scanning with Trivy"
    version = "1.0.0"
    supported_observable_types = ["docker_image"]
    tags = ["sca", "container", "critical"]
    
    timeout_seconds = 300  # 5 minutes
    requires_credentials = False
    parallel_safe = True
    
    async def analyze(
        self,
        observable: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run Trivy scan on container image.
        
        Args:
            observable: Observable with image name
            config: Optional config with:
                - severity: List of severities to report
                - scan_type: "vuln" | "config" | "secret"
        
        Returns:
            Analysis results with findings
        """
        image_name = observable["value"]
        config = config or {}
        
        self.logger.info(f"Running Trivy scan on image: {image_name}")
        
        try:
            from tools.trivy import trivy_wrapper
            
            severity = config.get("severity", ["CRITICAL", "HIGH", "MEDIUM"])
            scan_type = config.get("scan_type", "vuln")
            
            results = await trivy_wrapper.scan_image(
                image_name=image_name,
                severity=severity,
                scan_type=scan_type
            )
            
            # Parse findings
            findings = []
            for vuln in results.get("vulnerabilities", []):
                finding = self._parse_trivy_vulnerability(vuln, image_name)
                findings.append(finding)
            
            return {
                "status": "success",
                "findings": findings,
                "metadata": {
                    "image": image_name,
                    "total_vulnerabilities": results.get("total_vulnerabilities", 0),
                    "trivy_version": results.get("trivy_version", "unknown")
                }
            }
        
        except Exception as e:
            self.logger.error(f"Trivy analysis failed: {str(e)}", exc_info=True)
            return {
                "status": "failure",
                "findings": [],
                "metadata": {},
                "error": str(e)
            }
    
    def _parse_trivy_vulnerability(
        self,
        vuln: Dict[str, Any],
        image_name: str
    ) -> Dict[str, Any]:
        """
        Parse Trivy vulnerability into finding format.
        
        Args:
            vuln: Trivy vulnerability
            image_name: Docker image name
        
        Returns:
            Finding dictionary
        """
        # Map Trivy severity to standard
        severity_map = {
            "CRITICAL": "critical",
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
            "UNKNOWN": "info"
        }
        
        severity = severity_map.get(
            vuln.get("Severity", "UNKNOWN"),
            "medium"
        )
        
        # Extract CVE info
        vuln_id = vuln.get("VulnerabilityID", "")
        
        # Framework refs
        framework_refs = {}
        if vuln_id.startswith("CVE-"):
            framework_refs["cve"] = [vuln_id]
        
        return {
            "source": "sca",
            "tool": "trivy",
            "check_id": vuln_id,
            "title": f"{vuln.get('PkgName', '')} - {vuln_id}",
            "description": vuln.get("Description", ""),
            "severity": severity,
            "evidence": {
                "package": vuln.get("PkgName", ""),
                "installed_version": vuln.get("InstalledVersion", ""),
                "fixed_version": vuln.get("FixedVersion", ""),
                "vulnerability_id": vuln_id,
                "image": image_name,
                "references": vuln.get("References", [])
            },
            "remediation": f"Upgrade {vuln.get('PkgName')} to {vuln.get('FixedVersion', 'latest version')}",
            "framework_refs": framework_refs
        }
    
    def get_priority(self, observable: Dict[str, Any]) -> int:
        """Higher priority for production images."""
        metadata = observable.get("metadata", {})
        
        if metadata.get("environment") == "prod":
            return 15
        elif metadata.get("in_use"):
            return 10
        return 5

