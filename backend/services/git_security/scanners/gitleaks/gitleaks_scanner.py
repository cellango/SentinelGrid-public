"""
Gitleaks Scanner

Scans Git repositories for secrets and credentials using Gitleaks.
"""

import logging
import subprocess
import json
import tempfile
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class GitleaksScanner:
    """Scanner for detecting secrets in Git repositories."""
    
    def __init__(self, gitleaks_path: Optional[str] = None):
        """
        Initialize Gitleaks scanner.
        
        Args:
            gitleaks_path: Path to gitleaks binary (None to use system PATH)
        """
        self.gitleaks_path = gitleaks_path or "gitleaks"
    
    def scan_repository(
        self,
        repo_path: str,
        branch: str = "main",
        format: str = "json"
    ) -> List[Dict[str, Any]]:
        """
        Scan a Git repository for secrets.
        
        Args:
            repo_path: Path to Git repository
            branch: Branch to scan (default: main)
            format: Output format (json, sarif, csv)
        
        Returns:
            List of findings, each with:
            - description: Finding description
            - start_line: Line number
            - end_line: End line number
            - start_column: Start column
            - end_column: End column
            - match: Matched secret (redacted)
            - secret: Secret type detected
            - file: File path
            - commit: Commit SHA
            - message: Commit message
            - author: Commit author
            - email: Author email
            - date: Commit date
            - rule_id: Gitleaks rule ID
        """
        try:
            # Run gitleaks detect
            cmd = [
                self.gitleaks_path,
                "detect",
                "--source", repo_path,
                "--branch", branch,
                "--format", format,
                "--no-git",  # Don't use git history (faster)
                "--verbose"
            ]
            
            logger.info(f"Running gitleaks scan on {repo_path} (branch: {branch})")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                # Gitleaks returns 0 even when findings are detected
                # Check if there's output
                if result.stdout.strip():
                    try:
                        findings = json.loads(result.stdout)
                        if isinstance(findings, list):
                            return findings
                        elif isinstance(findings, dict) and "findings" in findings:
                            return findings["findings"]
                        else:
                            return []
                    except json.JSONDecodeError:
                        logger.warning("Gitleaks output is not valid JSON")
                        return []
                else:
                    return []
            elif result.returncode == 1:
                # Exit code 1 means secrets were found
                if result.stdout.strip():
                    try:
                        findings = json.loads(result.stdout)
                        if isinstance(findings, list):
                            return findings
                        elif isinstance(findings, dict) and "findings" in findings:
                            return findings["findings"]
                        else:
                            return []
                    except json.JSONDecodeError:
                        logger.warning("Gitleaks output is not valid JSON")
                        return []
                else:
                    return []
            else:
                logger.error(f"Gitleaks scan failed: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error(f"Gitleaks scan timed out for {repo_path}")
            return []
        except FileNotFoundError:
            logger.error(f"Gitleaks binary not found: {self.gitleaks_path}")
            return []
        except Exception as e:
            logger.error(f"Error running gitleaks scan: {e}", exc_info=True)
            return []
    
    def scan_file(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scan a single file for secrets.
        
        Args:
            file_path: Path to file
            content: File content (if None, reads from file_path)
        
        Returns:
            List of findings
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
                self.gitleaks_path,
                "detect",
                "--source", tmp_path,
                "--no-git",
                "--format", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            findings = []
            if result.stdout.strip():
                try:
                    findings = json.loads(result.stdout)
                    if isinstance(findings, dict) and "findings" in findings:
                        findings = findings["findings"]
                except json.JSONDecodeError:
                    pass
            
            # Cleanup temp file
            if content and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            return findings
            
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}", exc_info=True)
            return []
    
    def normalize_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a Gitleaks finding to SentinelGrid format.
        
        Args:
            finding: Raw Gitleaks finding
        
        Returns:
            Normalized finding
        """
        return {
            "finding_type": "secret",
            "severity": self._determine_severity(finding.get("RuleID", "")),
            "title": f"Secret detected: {finding.get('RuleID', 'Unknown')}",
            "description": finding.get("Description", ""),
            "file_path": finding.get("File", ""),
            "line_number": finding.get("StartLine", 0),
            "commit_sha": finding.get("Commit", ""),
            "commit_message": finding.get("Message", ""),
            "author_email": finding.get("Email", ""),
            "scanner_tool": "gitleaks",
            "scanner_rule_id": finding.get("RuleID", ""),
            "match": finding.get("Match", ""),  # Redacted
            "secret_type": finding.get("Secret", ""),
            "detected_at": finding.get("Date", "")
        }
    
    def _determine_severity(self, rule_id: str) -> str:
        """Determine severity based on rule ID."""
        critical_rules = [
            "aws-access-key",
            "aws-secret-key",
            "private-key",
            "slack-token",
            "github-token",
            "gitlab-token"
        ]
        
        high_rules = [
            "api-key",
            "password",
            "database-password",
            "oauth-token"
        ]
        
        rule_lower = rule_id.lower()
        
        if any(critical in rule_lower for critical in critical_rules):
            return "critical"
        elif any(high in rule_lower for high in high_rules):
            return "high"
        else:
            return "medium"

