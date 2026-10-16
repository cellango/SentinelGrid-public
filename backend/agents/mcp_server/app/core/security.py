"""Security and audit layer for MCP tools."""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import settings
from app.core.service_clients import clients

logger = logging.getLogger(__name__)


class MCPSecurityManager:
    """Security manager for MCP tool calls."""
    
    # High-risk tools that require approval
    HIGH_RISK_TOOLS = {
        "lock_account",
        "unlock_account",
        "revoke_sessions",
        "fix_public_bucket",
        "tag_resource",
        "delete_detection_rule",
        "update_firewall_rule",
    }
    
    # Read-only tools (safe)
    READ_ONLY_TOOLS = {
        "search_logs",
        "get_detections",
        "get_incidents",
        "get_user",
        "list_users",
        "list_playbooks",
        "get_playbook",
        "list_misconfigs",
        "get_misconfig",
        "lookup_cve",
        "search_cves",
        "get_mitre_technique",
        "search_controls",
        "get_control",
        "get_observable",
        "search_observables",
    }
    
    def __init__(self):
        """Initialize security manager."""
        self.audit_enabled = settings.MCP_AUDIT_ENABLED
        self.require_approval_for_high_risk = settings.MCP_REQUIRE_APPROVAL_FOR_HIGH_RISK
    
    async def authorize_tool_call(
        self,
        tool_name: str,
        tenant_id: str,
        user_id: str,
        params: Dict[str, Any]
    ) -> bool:
        """
        Check if user is authorized to call this tool with these parameters.
        
        Args:
            tool_name: Name of the MCP tool
            tenant_id: Tenant ID
            user_id: User ID making the call
            params: Tool parameters
        
        Returns:
            True if authorized, raises exception if not
        """
        logger.info(f"Authorizing tool call: {tool_name} for user {user_id} in tenant {tenant_id}")
        
        # Check if high-risk tool
        if tool_name in self.HIGH_RISK_TOOLS:
            if self.require_approval_for_high_risk:
                logger.warning(f"High-risk tool {tool_name} requires approval")
                # In production, this would check an approval workflow
                # For now, we'll allow but log heavily
        
        # Validate tenant_id is present in params for multi-tenant tools
        if "tenant_id" in params and params["tenant_id"] != tenant_id:
            logger.error(f"Tenant mismatch: requested {params['tenant_id']}, user is in {tenant_id}")
            raise PermissionError("Cannot access resources from different tenant")
        
        # Additional RBAC checks would go here
        # For now, we trust the internal service token
        
        return True
    
    async def audit_tool_call(
        self,
        tool_name: str,
        tenant_id: str,
        user_id: str,
        params: Dict[str, Any],
        result: Any,
        success: bool,
        error: Optional[str] = None
    ):
        """
        Log MCP tool call to SIEM for audit trail.
        
        Args:
            tool_name: Name of the MCP tool
            tenant_id: Tenant ID
            user_id: User ID
            params: Tool parameters
            result: Tool result
            success: Whether call succeeded
            error: Error message if failed
        """
        if not self.audit_enabled:
            return
        
        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "mcp_tool_call",
            "tool_name": tool_name,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "parameters": self._sanitize_params(params),
            "success": success,
            "high_risk": tool_name in self.HIGH_RISK_TOOLS,
        }
        
        if error:
            audit_event["error"] = error
        
        # Send to SIEM agent
        try:
            await clients.siem_agent.post(
                "/api/v1/events/ingest",
                json=audit_event,
                headers=clients.add_tenant_header(tenant_id)
            )
            logger.info(f"Audited tool call: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to audit tool call: {e}")
            # Don't fail the tool call if audit fails
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize parameters for logging (remove sensitive data).
        
        Args:
            params: Tool parameters
        
        Returns:
            Sanitized parameters
        """
        sanitized = {}
        sensitive_keys = {"password", "secret", "token", "api_key"}
        
        for key, value in params.items():
            if any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def sanitize_tool_output(self, output: str) -> str:
        """
        Sanitize tool output to prevent prompt injection.
        
        Args:
            output: Tool output string
        
        Returns:
            Sanitized output
        """
        # Remove potential prompt injection patterns
        dangerous_patterns = [
            r"<\|im_start\|>",
            r"<\|im_end\|>",
            r"###\s*System:",
            r"###\s*Assistant:",
            r"###\s*User:",
        ]
        
        sanitized = output
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, "[REMOVED]", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def is_high_risk_tool(self, tool_name: str) -> bool:
        """Check if tool is high-risk."""
        return tool_name in self.HIGH_RISK_TOOLS
    
    def is_read_only_tool(self, tool_name: str) -> bool:
        """Check if tool is read-only."""
        return tool_name in self.READ_ONLY_TOOLS


# Global security manager instance
security_manager = MCPSecurityManager()

