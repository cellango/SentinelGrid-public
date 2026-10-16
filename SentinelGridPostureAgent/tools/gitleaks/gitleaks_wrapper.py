"""Gitleaks CLI wrapper for secrets detection."""

import subprocess
import json
import tempfile
import asyncio
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def scan_repository(
    repo_url: str,
    scan_depth: int = 1
) -> Dict[str, Any]:
    """
    Scan a Git repository for secrets.
    
    Args:
        repo_url: Git repository URL
        scan_depth: Git clone depth (default: 1 for shallow clone)
    
    Returns:
        Dictionary with scan results
    """
    logger.info(f"Running Gitleaks scan on repository: {repo_url}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone repository
        logger.info("Cloning repository...")
        clone_cmd = ["git", "clone"]
        if scan_depth:
            clone_cmd.extend(["--depth", str(scan_depth)])
        clone_cmd.extend([repo_url, tmpdir])
        
        clone_process = await asyncio.create_subprocess_exec(
            *clone_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await clone_process.communicate()
        
        if clone_process.returncode != 0:
            logger.error("Git clone failed")
            return {
                "findings": [],
                "total_secrets": 0,
                "error": "Failed to clone repository"
            }
        
        # Run Gitleaks
        output_file = Path(tmpdir) / "gitleaks-report.json"
        
        cmd = [
            "gitleaks",
            "detect",
            "--source", tmpdir,
            "--report-path", str(output_file),
            "--report-format", "json",
            "--no-git"
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Gitleaks returns exit code 1 if secrets are found
            # So we check if the output file exists rather than exit code
            
            if output_file.exists():
                with open(output_file) as f:
                    findings = json.load(f)
            else:
                logger.info("No secrets found")
                findings = []
            
            return {
                "findings": findings,
                "total_secrets": len(findings),
                "repo_url": repo_url,
                "gitleaks_version": "8.x"  # TODO: Get actual version
            }
        
        except FileNotFoundError:
            logger.error("Gitleaks CLI not found. Install from: https://github.com/gitleaks/gitleaks")
            return {
                "findings": [],
                "total_secrets": 0,
                "gitleaks_version": "not_installed",
                "repo_url": repo_url,
                "error": "Gitleaks CLI not installed"
            }
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gitleaks output: {str(e)}")
            return {
                "findings": [],
                "total_secrets": 0,
                "gitleaks_version": "error",
                "repo_url": repo_url,
                "error": "Failed to parse Gitleaks output"
            }
        
        except Exception as e:
            logger.error(f"Error running Gitleaks: {str(e)}", exc_info=True)
            return {
                "findings": [],
                "total_secrets": 0,
                "gitleaks_version": "error",
                "repo_url": repo_url,
                "error": str(e)
            }


def is_gitleaks_installed() -> bool:
    """Check if Gitleaks CLI is installed."""
    try:
        result = subprocess.run(
            ["gitleaks", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

