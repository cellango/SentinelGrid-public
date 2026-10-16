"""
Trivy Scanner

Scans Git repositories for dependency vulnerabilities using Trivy.
"""

import logging
import subprocess
import json
import tempfile
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TrivyScanner:
    """Scanner for detecting dependency vulnerabilities."""
    
    def __init__(self, trivy_path: Optional[str] = None):
        """
        Initialize Trivy scanner.
        
        Args:
            trivy_path: Path to trivy binary (None to use system PATH)
        """
        self.trivy_path = trivy_path or "trivy"
    
    def scan_repository(
        self,
        repo_path: str,
        scan_type: str = "fs"  # fs (filesystem) or repo (git)
    ) -> Dict[str, Any]:
        """
        Scan a repository for dependency vulnerabilities.
        
        Args:
            repo_path: Path to repository
            scan_type: "fs" for filesystem scan, "repo" for git repository scan
        
        Returns:
            Scan results with vulnerabilities
        """
        try:
            cmd = [
                self.trivy_path,
                scan_type,
                "--format", "json",
                "--security-checks", "vuln",
                "--no-progress",
                repo_path
            ]
            
            logger.info(f"Running Trivy scan on {repo_path} (type: {scan_type})")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0 or result.returncode == 1:  # 1 = vulnerabilities found
                if result.stdout.strip():
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError:
                        logger.warning("Trivy output is not valid JSON")
                        return {}
                else:
                    return {}
            else:
                logger.error(f"Trivy scan failed: {result.stderr}")
                return {}
                
        except subprocess.TimeoutExpired:
            logger.error(f"Trivy scan timed out for {repo_path}")
            return {}
        except FileNotFoundError:
            logger.error(f"Trivy binary not found: {self.trivy_path}")
            return {}
        except Exception as e:
            logger.error(f"Error running Trivy scan: {e}", exc_info=True)
            return {}
    
    def scan_file(
        self,
        file_path: str,
        file_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scan a dependency file (package.json, requirements.txt, etc.).
        
        Args:
            file_path: Path to dependency file
            file_type: File type (auto-detected if None)
        
        Returns:
            Scan results
        """
        try:
            cmd = [
                self.trivy_path,
                "fs",
                "--format", "json",
                "--security-checks", "vuln",
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 or result.returncode == 1:
                if result.stdout.strip():
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError:
                        return {}
                else:
                    return {}
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}", exc_info=True)
            return {}
    
    def extract_vulnerabilities(self, trivy_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract vulnerabilities from Trivy scan results.
        
        Args:
            trivy_result: Trivy JSON output
        
        Returns:
            List of normalized vulnerabilities
        """
        vulnerabilities = []
        
        if "Results" not in trivy_result:
            return vulnerabilities
        
        for result in trivy_result.get("Results", []):
            target = result.get("Target", "")
            for vuln in result.get("Vulnerabilities", []):
                vulnerabilities.append({
                    "finding_type": "dependency_vulnerability",
                    "severity": self._map_severity(vuln.get("Severity", "UNKNOWN")),
                    "title": f"{vuln.get('VulnerabilityID', 'CVE')} in {vuln.get('PkgName', '')}",
                    "description": vuln.get("Description", ""),
                    "file_path": target,
                    "scanner_tool": "trivy",
                    "scanner_rule_id": vuln.get("VulnerabilityID", ""),
                    "package_name": vuln.get("PkgName", ""),
                    "package_version": vuln.get("InstalledVersion", ""),
                    "fixed_version": vuln.get("FixedVersion", ""),
                    "cve_id": vuln.get("VulnerabilityID", ""),
                    "cvss_score": vuln.get("CVSS", {}).get("nvd", {}).get("V3Score", 0) if vuln.get("CVSS") else None,
                    "published_date": vuln.get("PublishedDate", ""),
                    "detected_at": trivy_result.get("CreatedAt", "")
                })
        
        return vulnerabilities
    
    def _map_severity(self, trivy_severity: str) -> str:
        """Map Trivy severity to SentinelGrid severity."""
        mapping = {
            "CRITICAL": "critical",
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
            "UNKNOWN": "info"
        }
        return mapping.get(trivy_severity.upper(), "medium")

