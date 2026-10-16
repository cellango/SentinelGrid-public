"""Prowler CSPM analyzer for AWS."""

from analyzers.base_analyzer import BaseAnalyzer
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ProwlerAWSAnalyzer(BaseAnalyzer):
    """
    Prowler CSPM analyzer for AWS accounts and resources.
    
    Runs Prowler security checks against AWS infrastructure.
    """
    
    name = "prowler-aws-cspm"
    description = "AWS cloud security posture management with Prowler"
    version = "1.0.0"
    supported_observable_types = [
        "aws_account",
        "aws_s3_bucket",
        "aws_ec2_instance",
        "aws_iam_role",
        "aws_rds_instance",
        "aws_lambda_function"
    ]
    tags = ["cspm", "cloud", "aws", "critical"]
    
    timeout_seconds = 600  # 10 minutes for full account scans
    requires_credentials = True
    parallel_safe = True
    
    async def analyze(
        self,
        observable: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run Prowler analysis on AWS observable.
        
        Args:
            observable: Observable with AWS resource info
            config: Optional config with:
                - role_arn: IAM role to assume
                - external_id: External ID for role assumption
                - regions: List of regions to scan
                - checks: Specific checks to run
        
        Returns:
            Analysis results with findings
        """
        obs_type = observable["type"]
        obs_value = observable["value"]
        config = config or {}
        
        self.logger.info(f"Running Prowler on {obs_type}: {obs_value}")
        
        try:
            # Import Prowler wrapper (will be created in tools/)
            from tools.prowler import prowler_wrapper
            
            if obs_type == "aws_account":
                # Full account scan
                account_id = obs_value
                results = await prowler_wrapper.scan_account(
                    account_id=account_id,
                    role_arn=config.get("role_arn"),
                    external_id=config.get("external_id"),
                    regions=config.get("regions"),
                    checks=config.get("checks")
                )
            else:
                # Resource-specific scan
                resource_arn = obs_value
                results = await prowler_wrapper.scan_resource(
                    resource_arn=resource_arn,
                    role_arn=config.get("role_arn"),
                    external_id=config.get("external_id")
                )
            
            # Parse findings
            findings = []
            for check in results.get("checks", []):
                if check["status"] == "FAIL":
                    finding = self._parse_prowler_check(check)
                    findings.append(finding)
            
            return {
                "status": "success",
                "findings": findings,
                "metadata": {
                    "checks_run": len(results.get("checks", [])),
                    "resources_scanned": results.get("resources_scanned", 0),
                    "duration_seconds": results.get("duration", 0),
                    "prowler_version": results.get("prowler_version", "unknown")
                }
            }
        
        except Exception as e:
            self.logger.error(f"Prowler analysis failed: {str(e)}", exc_info=True)
            return {
                "status": "failure",
                "findings": [],
                "metadata": {},
                "error": str(e)
            }
    
    def _parse_prowler_check(self, check: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Prowler check result into finding format.
        
        Args:
            check: Prowler check result
        
        Returns:
            Finding dictionary
        """
        # Map Prowler severity to standard severity
        severity_map = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "informational": "info"
        }
        
        severity = severity_map.get(
            check.get("severity", "medium").lower(),
            "medium"
        )
        
        # Extract framework references
        framework_refs = {}
        compliance = check.get("compliance", {})
        if compliance:
            for framework, controls in compliance.items():
                if isinstance(controls, list):
                    framework_refs[framework.lower()] = controls
        
        return {
            "source": "cspm",
            "tool": "prowler",
            "check_id": check.get("check_id", ""),
            "title": check.get("check_title", "Unknown check"),
            "description": check.get("check_description", ""),
            "severity": severity,
            "evidence": {
                "resource_id": check.get("resource_id", ""),
                "resource_type": check.get("resource_type", ""),
                "region": check.get("region", ""),
                "service": check.get("service", ""),
                "status": check.get("status", ""),
                "status_extended": check.get("status_extended", ""),
                "resource_details": check.get("resource_details", {})
            },
            "remediation": check.get("remediation", ""),
            "framework_refs": framework_refs
        }
    
    def should_run(self, observable: Dict[str, Any]) -> bool:
        """
        Determine if Prowler should run.
        
        Always run for supported AWS observable types.
        """
        return observable.get("type") in self.supported_observable_types
    
    def get_priority(self, observable: Dict[str, Any]) -> int:
        """
        Get execution priority.
        
        Higher priority for production environments.
        """
        metadata = observable.get("metadata", {})
        environment = metadata.get("environment", "").lower()
        
        if environment == "prod" or environment == "production":
            return 20  # High priority
        elif environment == "staging":
            return 10  # Medium priority
        else:
            return 5  # Lower priority for dev
    
    def estimate_duration(self, observable: Dict[str, Any]) -> int:
        """
        Estimate scan duration.
        
        Account scans take longer than resource scans.
        """
        if observable.get("type") == "aws_account":
            return 600  # 10 minutes for full account
        else:
            return 60  # 1 minute for single resource

