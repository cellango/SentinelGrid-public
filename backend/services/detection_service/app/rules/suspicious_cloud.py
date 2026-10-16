"""Suspicious Cloud Actions detection rule."""

import logging
from typing import List, Dict, Any
from app.rules.base import BaseRule

logger = logging.getLogger(__name__)


class SuspiciousCloudRule(BaseRule):
    """Detect suspicious cloud actions (S3 public, IAM changes, etc.)."""
    
    def evaluate(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate events for suspicious cloud actions.
        
        Patterns:
        - S3 bucket made public
        - IAM policy changed
        - Security group modified
        - Unusual API calls
        """
        alerts = []
        
        # Extract configuration
        suspicious_actions = self.pattern.get("suspicious_actions", [
            "PutBucketPolicy",
            "PutBucketAcl",
            "PutBucketPublicAccessBlock",
            "PutRolePolicy",
            "AttachUserPolicy",
            "AttachRolePolicy",
            "AuthorizeSecurityGroupIngress",
            "ModifySecurityGroupRules",
        ])
        
        for event in events:
            # Check event type and name
            event_type = event.get("event_type", "").lower()
            event_name = event.get("event_name", "")
            action = event.get("action", "")
            
            # Check if this is a suspicious action
            is_suspicious = False
            suspicious_reason = None
            
            # Check AWS CloudTrail events
            if event_name in suspicious_actions:
                is_suspicious = True
                suspicious_reason = f"AWS action: {event_name}"
            
            # Check for specific patterns
            if not is_suspicious:
                # S3 bucket made public
                request_params = event.get("request_parameters", {})
                if request_params:
                    # Check for public access
                    if "PublicAccessBlockConfiguration" in str(request_params):
                        block_config = request_params.get("PublicAccessBlockConfiguration", {})
                        if not block_config.get("BlockPublicAcls", True):
                            is_suspicious = True
                            suspicious_reason = "S3 bucket public access enabled"
                    
                    # Check for public ACL
                    if "AccessControlPolicy" in str(request_params):
                        is_suspicious = True
                        suspicious_reason = "S3 bucket ACL modified"
                
                # IAM policy changes
                if "iam" in event_type and ("policy" in event_type or "role" in event_type):
                    if "attach" in action.lower() or "put" in action.lower():
                        is_suspicious = True
                        suspicious_reason = "IAM policy or role modified"
                
                # Security group changes
                if "securitygroup" in event_type.lower() or "security_group" in event_type.lower():
                    if "authorize" in action.lower() or "modify" in action.lower():
                        is_suspicious = True
                        suspicious_reason = "Security group modified"
            
            if is_suspicious:
                # Extract resource information
                resource_type = event.get("resource_type")
                resource_name = event.get("resource_name")
                user = event.get("user", {})
                user_name = user.get("name") or user.get("email") or user.get("arn")
                
                # Create alert
                alert = self.create_alert(
                    title=f"Suspicious Cloud Action - {suspicious_reason}",
                    description=(
                        f"Suspicious cloud action detected: {suspicious_reason}. "
                        f"Action: {event_name or action}. "
                        f"Resource: {resource_type or 'unknown'} ({resource_name or 'unknown'}). "
                        f"User: {user_name or 'unknown'}"
                    ),
                    events=[event],
                    metadata={
                        "event_name": event_name,
                        "action": action,
                        "resource_type": resource_type,
                        "resource_name": resource_name,
                        "user": user_name,
                        "suspicious_reason": suspicious_reason,
                        "event_timestamp": event.get("@timestamp") or event.get("timestamp"),
                    },
                )
                alerts.append(alert)
        
        return alerts
    
    def get_rule_type(self) -> str:
        return "suspicious_cloud"

