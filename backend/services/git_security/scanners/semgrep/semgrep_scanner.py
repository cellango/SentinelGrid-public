"""
Semgrep Scanner

Scans Git repositories for code issues and security patterns using Semgrep.
"""

import logging
import subprocess
import json
import tempfile
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SemgrepScanner:
    """Scanner for detecting code issues and security patterns."""
    
    def __init__(self, semgrep_path: Optional[str] = None):
        """
        Initialize Semgrep scanner.
        
        Args:
            semgrep_path: Path to semgrep binary (None to use system PATH)
        """
        self.semgrep_path = semgrep_path or "semgrep"
    
    def scan_repository(
        self,
        repo_path: str,
        config: str = "auto",  # auto, p/security-audit, p/python, etc.
        severity: Optional[str] = None  # INFO, WARNING, ERROR
    ) -> Dict[str, Any]:
        """
        Scan a repository for code issues.
        
        Args:
            repo_path: Path to repository
            config: Semgrep config (auto, p/security-audit, etc.)
            severity: Filter by severity (None for all)
        
        Returns:
            Scan results with findings
        """
        try:
            cmd = [
                self.semgrep_path,
                "scan",
                "--config", config,
                "--json",
                "--no-git-ignore",
                repo_path
            ]
            
            if severity:
                cmd.extend(["--severity", severity])
            
            logger.info(f"Running Semgrep scan on {repo_path} (config: {config})")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0 or result.returncode == 1:  # 1 = findings found
                if result.stdout.strip():
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError:
                        logger.warning("Semgrep output is not valid JSON")
                        return {}
                else:
                    return {}
            else:
                logger.error(f"Semgrep scan failed: {result.stderr}")
                return {}
                
        except subprocess.TimeoutExpired:
            logger.error(f"Semgrep scan timed out for {repo_path}")
            return {}
        except FileNotFoundError:
            logger.error(f"Semgrep binary not found: {self.semgrep_path}")
            return {}
        except Exception as e:
            logger.error(f"Error running Semgrep scan: {e}", exc_info=True)
            return {}
    
    def scan_file(
        self,
        file_path: str,
        content: Optional[str] = None,
        config: str = "auto"
    ) -> Dict[str, Any]:
        """
        Scan a single file for code issues.
        
        Args:
            file_path: Path to file
            content: File content (if None, reads from file_path)
            config: Semgrep config
        
        Returns:
            Scan results
        """
        try:
            # Create temp file if content provided
            if content:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=Path(file_path).suffix) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
            else:
                tmp_path = file_path
            
            cmd = [
                self.semgrep_path,
                "scan",
                "--config", config,
                "--json",
                tmp_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            scan_result = {}
            if result.stdout.strip():
                try:
                    scan_result = json.loads(result.stdout)
                except json.JSONDecodeError:
                    pass
            
            # Cleanup temp file
            if content and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            return scan_result
            
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}", exc_info=True)
            return {}
    
    def extract_findings(self, semgrep_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract findings from Semgrep scan results.
        
        Args:
            semgrep_result: Semgrep JSON output
        
        Returns:
            List of normalized findings
        """
        findings = []
        
        for result in semgrep_result.get("results", []):
            finding = {
                "finding_type": "code_issue",
                "severity": self._map_severity(result.get("extra", {}).get("severity", "INFO")),
                "title": result.get("check_id", "Code Issue"),
                "description": result.get("message", ""),
                "file_path": result.get("path", ""),
                "line_number": result.get("start", {}).get("line", 0),
                "end_line": result.get("end", {}).get("line", 0),
                "start_column": result.get("start", {}).get("col", 0),
                "end_column": result.get("end", {}).get("col", 0),
                "scanner_tool": "semgrep",
                "scanner_rule_id": result.get("check_id", ""),
                "rule_message": result.get("message", ""),
                "rule_metadata": result.get("extra", {}).get("metadata", {}),
                "code_snippet": result.get("extra", {}).get("lines", ""),
                "detected_at": semgrep_result.get("time", "")
            }
            findings.append(finding)
        
        return findings
    
    def _map_severity(self, semgrep_severity: str) -> str:
        """Map Semgrep severity to SentinelGrid severity."""
        mapping = {
            "ERROR": "high",
            "WARNING": "medium",
            "INFO": "low"
        }
        return mapping.get(semgrep_severity.upper(), "medium")

