"""OWASP ZAP DAST analyzer for web applications."""

from analyzers.base_analyzer import BaseAnalyzer
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ZAPAnalyzer(BaseAnalyzer):
    """
    OWASP ZAP dynamic application security testing analyzer.
    
    Scans web applications for vulnerabilities.
    """
    
    name = "zap-dast"
    description = "OWASP ZAP dynamic application security testing"
    version = "1.0.0"
    supported_observable_types = ["web_application", "api_endpoint"]
    tags = ["dast", "webapp", "critical"]
    
    timeout_seconds = 900  # 15 minutes for full scan
    requires_credentials = False  # Can run unauthenticated
    parallel_safe = True
    
    async def analyze(
        self,
        observable: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run ZAP scan on web application.
        
        Args:
            observable: Observable with URL
            config: Optional config with:
                - scan_type: "quick" | "full" | "api"
                - auth: Authentication configuration
                - scope: URLs to include/exclude
        
        Returns:
            Analysis results with findings
        """
        url = observable["value"]
        config = config or {}
        
        self.logger.info(f"Running ZAP scan on: {url}")
        
        try:
            # Import ZAP wrapper (will be created in tools/)
            from tools.zap import zap_wrapper
            
            scan_type = config.get("scan_type", "full")
            
            results = await zap_wrapper.scan(
                url=url,
                scan_type=scan_type,
                auth_config=config.get("auth"),
                scope_config=config.get("scope")
            )
            
            # Parse findings
            findings = []
            for alert in results.get("alerts", []):
                finding = self._parse_zap_alert(alert)
                findings.append(finding)
            
            return {
                "status": "success",
                "findings": findings,
                "metadata": {
                    "urls_tested": results.get("urls_tested", 0),
                    "duration_seconds": results.get("duration", 0),
                    "scan_type": scan_type,
                    "zap_version": results.get("zap_version", "unknown")
                }
            }
        
        except Exception as e:
            self.logger.error(f"ZAP analysis failed: {str(e)}", exc_info=True)
            return {
                "status": "failure",
                "findings": [],
                "metadata": {},
                "error": str(e)
            }
    
    def _parse_zap_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse ZAP alert into finding format.
        
        Args:
            alert: ZAP alert
        
        Returns:
            Finding dictionary
        """
        # Map ZAP risk to severity
        risk_map = {
            "High": "high",
            "Medium": "medium",
            "Low": "low",
            "Informational": "info"
        }
        
        severity = risk_map.get(alert.get("risk", "Medium"), "medium")
        
        # Map to OWASP Top 10 if available
        framework_refs = {}
        cwe_id = alert.get("cweid")
        if cwe_id:
            framework_refs["cwe"] = [str(cwe_id)]
        
        owasp_category = alert.get("tags", {}).get("OWASP_2021")
        if owasp_category:
            framework_refs["owasp_2021"] = [owasp_category]
        
        return {
            "source": "dast",
            "tool": "zap",
            "check_id": alert.get("pluginid", ""),
            "title": alert.get("name", "Unknown vulnerability"),
            "description": alert.get("description", ""),
            "severity": severity,
            "evidence": {
                "url": alert.get("url", ""),
                "method": alert.get("method", ""),
                "param": alert.get("param", ""),
                "attack": alert.get("attack", ""),
                "evidence": alert.get("evidence", ""),
                "confidence": alert.get("confidence", "")
            },
            "remediation": alert.get("solution", ""),
            "framework_refs": framework_refs
        }
    
    def should_run(self, observable: Dict[str, Any]) -> bool:
        """
        Determine if ZAP should run.
        
        Only run on HTTP/HTTPS URLs.
        """
        if observable.get("type") not in self.supported_observable_types:
            return False
        
        url = observable.get("value", "")
        return url.startswith("http://") or url.startswith("https://")
    
    def get_priority(self, observable: Dict[str, Any]) -> int:
        """
        Get execution priority.
        
        Higher priority for production web apps.
        """
        metadata = observable.get("metadata", {})
        
        # High priority for prod
        if metadata.get("environment") == "prod":
            return 15
        
        # Medium priority if has authentication
        if metadata.get("requires_auth"):
            return 10
        
        return 5
    
    def estimate_duration(self, observable: Dict[str, Any]) -> int:
        """
        Estimate scan duration based on scan type.
        """
        metadata = observable.get("metadata", {})
        scan_type = metadata.get("scan_type", "full")
        
        if scan_type == "quick":
            return 300  # 5 minutes
        elif scan_type == "api":
            return 600  # 10 minutes
        else:  # full
            return 900  # 15 minutes

