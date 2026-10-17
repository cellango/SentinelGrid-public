"""Security and audit layer for MCP tools."""

import logging
import re
from typing import Dict, Any

from app.core.tool_admission import WIRE_TOOL_MAP, require_tool_admission

logger = logging.getLogger(__name__)


class MCPSecurityManager:
    """Security manager for MCP tool calls."""
    
    # Effect labels are metadata only. Reads also require identity/data admission.
    HIGH_RISK_TOOLS = frozenset(name for name, (_, effect) in WIRE_TOOL_MAP.items() if effect == "write")
    READ_ONLY_TOOLS = frozenset(name for name, (_, effect) in WIRE_TOOL_MAP.items() if effect == "read")

    def __init__(self):
        # Legacy attributes cannot enable execution or authenticate an audit event.
        self.audit_enabled = True
        self.require_approval_for_high_risk = True

    async def authorize_tool_call(self, tool_name, tenant_id, user_id, params):
        return require_tool_admission(tool_name, tenant_id, user_id, params)

    async def audit_tool_call(self, tool_name, tenant_id, user_id, params,
                              result, success, error=None):
        # No arbitrary string identities/results may be emitted as trusted audit.
        # A durable admitted audit boundary is required before enabling this path.
        require_tool_admission(tool_name, tenant_id, user_id, params)

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
        Strip legacy presentation markers; output remains untrusted evidence.
        
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

