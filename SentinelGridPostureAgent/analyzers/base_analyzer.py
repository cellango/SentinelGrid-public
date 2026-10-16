"""Base analyzer class - all analyzers inherit from this."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """
    Base class for all security analyzers.
    
    Analyzers are tools that analyze observables (assets, repos, images, etc.)
    and produce security findings.
    
    Example:
        class ProwlerAnalyzer(BaseAnalyzer):
            name = "prowler-aws-cspm"
            description = "AWS cloud security posture scanning with Prowler"
            supported_observable_types = ["aws_account", "aws_s3_bucket"]
            tags = ["cspm", "cloud", "aws", "critical"]
            
            async def analyze(self, observable, config=None):
                # Run Prowler scan
                results = await run_prowler(observable["value"])
                return {"status": "success", "findings": [...]}
    """
    
    # Analyzer metadata (override in subclass)
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    supported_observable_types: List[str] = []
    tags: List[str] = []  # e.g., ["cloud", "iac", "critical", "fast", "expensive"]
    
    # Execution constraints
    timeout_seconds: int = 300  # Default 5 minutes
    requires_credentials: bool = True
    parallel_safe: bool = True  # Can run in parallel with other analyzers
    
    def __init__(self):
        """Initialize analyzer."""
        self.logger = logging.getLogger(f"analyzer.{self.name}")
        
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must define 'name'")
        if not self.supported_observable_types:
            raise ValueError(f"{self.name} must define 'supported_observable_types'")
    
    @abstractmethod
    async def analyze(
        self, 
        observable: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run analysis on an observable.
        
        Args:
            observable: Observable data with keys:
                - type: Observable type (e.g., "web_application")
                - value: Observable value (e.g., "https://app.example.com")
                - metadata: Additional metadata
            config: Analyzer-specific configuration
        
        Returns:
            Dictionary with keys:
                - status: "success" | "failure"
                - findings: List of finding dictionaries
                - metadata: Analysis metadata (duration, resources scanned, etc.)
                - error: Error message if status is "failure"
        
        Finding format:
            {
                "source": "cspm" | "iac" | "dast" | "sast" | "sca" | "secret_scan",
                "tool": "prowler" | "zap" | "trivy" | etc.,
                "title": "Finding title",
                "description": "Detailed description",
                "severity": "critical" | "high" | "medium" | "low" | "info",
                "evidence": {...},  # Tool-specific evidence
                "remediation": "How to fix",
                "check_id": "tool-specific-check-id",
                "framework_refs": {"cis": ["1.1"], "nist": ["AC-2"]},
            }
        """
        pass
    
    def should_run(self, observable: Dict[str, Any]) -> bool:
        """
        Determine if this analyzer should run for the given observable.
        
        Override this method for custom logic beyond just checking observable_type.
        
        Example:
            def should_run(self, observable):
                # Only run Checkov if repo contains IaC files
                if observable["type"] != "git_repository":
                    return False
                metadata = observable.get("metadata", {})
                return (
                    metadata.get("has_terraform") or
                    metadata.get("has_cloudformation") or
                    metadata.get("has_kubernetes_manifests")
                )
        
        Args:
            observable: Observable dictionary
        
        Returns:
            True if analyzer should run, False otherwise
        """
        return observable.get("type") in self.supported_observable_types
    
    def get_priority(self, observable: Dict[str, Any]) -> int:
        """
        Get execution priority for this analyzer on the given observable.
        
        Higher numbers = higher priority (run first).
        
        Override to implement custom prioritization logic.
        
        Args:
            observable: Observable dictionary
        
        Returns:
            Priority integer (default: 0)
        """
        # Default: "critical" tagged analyzers get higher priority
        if "critical" in self.tags:
            return 10
        elif "high-priority" in self.tags:
            return 5
        return 0
    
    def estimate_duration(self, observable: Dict[str, Any]) -> int:
        """
        Estimate analysis duration in seconds.
        
        Override to provide better estimates based on observable characteristics.
        
        Args:
            observable: Observable dictionary
        
        Returns:
            Estimated duration in seconds
        """
        return self.timeout_seconds
    
    async def validate_config(self, config: Optional[Dict[str, Any]]) -> bool:
        """
        Validate analyzer configuration.
        
        Override to implement custom validation logic.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            True if valid, False otherwise
        """
        return True
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, version={self.version})>"

