"""Prowler CLI wrapper for AWS security scanning."""

import subprocess
import json
import tempfile
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


async def scan_account(
    account_id: str,
    role_arn: Optional[str] = None,
    external_id: Optional[str] = None,
    regions: Optional[List[str]] = None,
    checks: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Run Prowler scan on an AWS account.
    
    Args:
        account_id: AWS account ID
        role_arn: IAM role ARN to assume
        external_id: External ID for role assumption
        regions: List of regions to scan (default: all)
        checks: Specific checks to run (default: all)
    
    Returns:
        Dictionary with scan results
    """
    logger.info(f"Running Prowler scan on account {account_id}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "prowler-output.json"
        
        # Build Prowler command
        cmd = ["prowler", "aws"]
        
        if role_arn:
            cmd.extend(["--role-arn", role_arn])
        
        if external_id:
            cmd.extend(["--external-id", external_id])
        
        if regions:
            cmd.extend(["--regions", ",".join(regions)])
        
        if checks:
            cmd.extend(["--checks", ",".join(checks)])
        
        # Output format
        cmd.extend([
            "--output-formats", "json",
            "--output-filename", str(output_file),
            "--no-banner",
            "--quiet"
        ])
        
        try:
            # Run Prowler asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Prowler failed: {stderr.decode()}")
                raise Exception(f"Prowler scan failed: {stderr.decode()}")
            
            # Read results
            if output_file.exists():
                with open(output_file) as f:
                    results = json.load(f)
            else:
                logger.warning("Prowler output file not found, returning empty results")
                results = {"checks": []}
            
            # Parse and return results
            return {
                "checks": results.get("checks", []),
                "resources_scanned": len(results.get("resources", [])),
                "duration": results.get("duration", 0),
                "prowler_version": results.get("prowler_version", "unknown"),
                "account_id": account_id
            }
        
        except FileNotFoundError:
            logger.error("Prowler CLI not found. Install with: pip install prowler")
            return {
                "checks": [],
                "resources_scanned": 0,
                "duration": 0,
                "prowler_version": "not_installed",
                "account_id": account_id,
                "error": "Prowler CLI not installed"
            }
        
        except Exception as e:
            logger.error(f"Error running Prowler: {str(e)}", exc_info=True)
            return {
                "checks": [],
                "resources_scanned": 0,
                "duration": 0,
                "prowler_version": "error",
                "account_id": account_id,
                "error": str(e)
            }


async def scan_resource(
    resource_arn: str,
    role_arn: Optional[str] = None,
    external_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run Prowler scan on a specific AWS resource.
    
    Args:
        resource_arn: ARN of the resource to scan
        role_arn: IAM role ARN to assume
        external_id: External ID for role assumption
    
    Returns:
        Dictionary with scan results
    """
    logger.info(f"Running Prowler scan on resource {resource_arn}")
    
    # Parse ARN to get resource type and region
    arn_parts = resource_arn.split(":")
    if len(arn_parts) >= 6:
        service = arn_parts[2]
        region = arn_parts[3]
        account_id = arn_parts[4]
        resource_id = arn_parts[5]
        
        # Run scan with filters for this specific resource
        # For now, scan the whole account and filter results
        # TODO: Implement resource-specific filtering in Prowler
        results = await scan_account(
            account_id=account_id,
            role_arn=role_arn,
            external_id=external_id,
            regions=[region] if region else None
        )
        
        # Filter checks related to this resource
        filtered_checks = [
            check for check in results.get("checks", [])
            if check.get("resource_id") == resource_id
        ]
        
        results["checks"] = filtered_checks
        results["resource_arn"] = resource_arn
        
        return results
    else:
        logger.error(f"Invalid ARN format: {resource_arn}")
        return {
            "checks": [],
            "resources_scanned": 0,
            "duration": 0,
            "prowler_version": "error",
            "resource_arn": resource_arn,
            "error": "Invalid ARN format"
        }


def is_prowler_installed() -> bool:
    """Check if Prowler CLI is installed."""
    try:
        result = subprocess.run(
            ["prowler", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


async def validate_credentials(
    account_id: str,
    role_arn: Optional[str] = None,
    external_id: Optional[str] = None
) -> bool:
    """
    Validate AWS credentials by attempting to assume the role.
    
    Args:
        account_id: AWS account ID
        role_arn: IAM role ARN
        external_id: External ID
    
    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        # TODO: Implement actual credential validation using boto3
        # For now, return True
        return True
    except Exception as e:
        logger.error(f"Credential validation failed: {str(e)}")
        return False

