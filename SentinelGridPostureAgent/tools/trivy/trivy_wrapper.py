"""Trivy CLI wrapper for vulnerability scanning."""

import subprocess
import json
import asyncio
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


async def scan_image(
    image_name: str,
    severity: Optional[List[str]] = None,
    scan_type: str = "vuln"
) -> Dict[str, Any]:
    """
    Scan a container image for vulnerabilities.
    
    Args:
        image_name: Docker image name (e.g., "nginx:latest")
        severity: List of severities to report (default: all)
        scan_type: "vuln" | "config" | "secret"
    
    Returns:
        Dictionary with scan results
    """
    logger.info(f"Running Trivy scan on image: {image_name}")
    
    # Build Trivy command
    cmd = [
        "trivy",
        "image",
        "--format", "json",
        "--quiet"
    ]
    
    if severity:
        cmd.extend(["--severity", ",".join(severity)])
    
    if scan_type:
        cmd.extend(["--scanners", scan_type])
    
    cmd.append(image_name)
    
    try:
        # Run Trivy asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Trivy failed: {stderr.decode()}")
            raise Exception(f"Trivy scan failed: {stderr.decode()}")
        
        # Parse results
        results = json.loads(stdout.decode())
        
        # Extract vulnerabilities
        vulnerabilities = []
        for result in results.get("Results", []):
            for vuln in result.get("Vulnerabilities", []):
                vulnerabilities.append(vuln)
        
        return {
            "vulnerabilities": vulnerabilities,
            "image_name": image_name,
            "total_vulnerabilities": len(vulnerabilities),
            "trivy_version": results.get("SchemaVersion", "unknown")
        }
    
    except FileNotFoundError:
        logger.error("Trivy CLI not found. Install from: https://github.com/aquasecurity/trivy")
        return {
            "vulnerabilities": [],
            "image_name": image_name,
            "total_vulnerabilities": 0,
            "trivy_version": "not_installed",
            "error": "Trivy CLI not installed"
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Trivy output: {str(e)}")
        return {
            "vulnerabilities": [],
            "image_name": image_name,
            "total_vulnerabilities": 0,
            "trivy_version": "error",
            "error": "Failed to parse Trivy output"
        }
    
    except Exception as e:
        logger.error(f"Error running Trivy: {str(e)}", exc_info=True)
        return {
            "vulnerabilities": [],
            "image_name": image_name,
            "total_vulnerabilities": 0,
            "trivy_version": "error",
            "error": str(e)
        }


async def scan_filesystem(
    path: str,
    severity: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Scan a filesystem for vulnerabilities.
    
    Args:
        path: Path to scan
        severity: List of severities to report
    
    Returns:
        Dictionary with scan results
    """
    logger.info(f"Running Trivy filesystem scan on: {path}")
    
    cmd = [
        "trivy",
        "fs",
        "--format", "json",
        "--quiet"
    ]
    
    if severity:
        cmd.extend(["--severity", ",".join(severity)])
    
    cmd.append(path)
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Trivy failed: {stderr.decode()}")
            raise Exception(f"Trivy scan failed: {stderr.decode()}")
        
        results = json.loads(stdout.decode())
        
        vulnerabilities = []
        for result in results.get("Results", []):
            for vuln in result.get("Vulnerabilities", []):
                vulnerabilities.append(vuln)
        
        return {
            "vulnerabilities": vulnerabilities,
            "path": path,
            "total_vulnerabilities": len(vulnerabilities)
        }
    
    except Exception as e:
        logger.error(f"Error running Trivy: {str(e)}", exc_info=True)
        return {
            "vulnerabilities": [],
            "path": path,
            "total_vulnerabilities": 0,
            "error": str(e)
        }


def is_trivy_installed() -> bool:
    """Check if Trivy CLI is installed."""
    try:
        result = subprocess.run(
            ["trivy", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

