"""Checkov CLI wrapper for IaC security scanning."""

import subprocess
import json
import tempfile
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


async def scan_repository(
    repo_url: str,
    frameworks: Optional[List[str]] = None,
    checks: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Scan a Git repository for IaC security issues.
    
    Args:
        repo_url: Git repository URL
        frameworks: Frameworks to check (terraform, cloudformation, kubernetes, etc.)
        checks: Specific checks to run
    
    Returns:
        Dictionary with scan results
    """
    logger.info(f"Running Checkov scan on repository: {repo_url}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone repository
        logger.info("Cloning repository...")
        clone_process = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", repo_url, tmpdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await clone_process.communicate()
        
        if clone_process.returncode != 0:
            logger.error("Git clone failed")
            return {
                "passed_checks": [],
                "failed_checks": [],
                "skipped_checks": [],
                "summary": {},
                "error": "Failed to clone repository"
            }
        
        # Run Checkov
        cmd = [
            "checkov",
            "--directory", tmpdir,
            "--output", "json",
            "--quiet"
        ]
        
        if frameworks:
            cmd.extend(["--framework", ",".join(frameworks)])
        
        if checks:
            for check in checks:
                cmd.extend(["--check", check])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Checkov returns non-zero if findings exist, so check output
            if stdout:
                results = json.loads(stdout.decode())
            else:
                logger.warning("Checkov produced no output")
                results = {}
            
            # Parse results
            passed_checks = results.get("passed_checks", [])
            failed_checks = results.get("failed_checks", [])
            skipped_checks = results.get("skipped_checks", [])
            
            summary = results.get("summary", {})
            if not summary and failed_checks:
                # Calculate summary if not provided
                summary = {
                    "passed": len(passed_checks),
                    "failed": len(failed_checks),
                    "skipped": len(skipped_checks),
                    "files_scanned": len(set(c.get("file_path") for c in failed_checks))
                }
            
            return {
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
                "skipped_checks": skipped_checks,
                "summary": summary,
                "checkov_version": results.get("checkov_version", "unknown"),
                "repo_url": repo_url
            }
        
        except FileNotFoundError:
            logger.error("Checkov CLI not found. Install with: pip install checkov")
            return {
                "passed_checks": [],
                "failed_checks": [],
                "skipped_checks": [],
                "summary": {},
                "checkov_version": "not_installed",
                "repo_url": repo_url,
                "error": "Checkov CLI not installed"
            }
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Checkov output: {str(e)}")
            return {
                "passed_checks": [],
                "failed_checks": [],
                "skipped_checks": [],
                "summary": {},
                "checkov_version": "error",
                "repo_url": repo_url,
                "error": "Failed to parse Checkov output"
            }
        
        except Exception as e:
            logger.error(f"Error running Checkov: {str(e)}", exc_info=True)
            return {
                "passed_checks": [],
                "failed_checks": [],
                "skipped_checks": [],
                "summary": {},
                "checkov_version": "error",
                "repo_url": repo_url,
                "error": str(e)
            }


def is_checkov_installed() -> bool:
    """Check if Checkov CLI is installed."""
    try:
        result = subprocess.run(
            ["checkov", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

