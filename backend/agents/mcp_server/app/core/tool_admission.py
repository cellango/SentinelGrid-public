"""Legacy wire-name map and source-preview denial boundary.

Metadata does not authenticate callers, grant capabilities or verify effects.
No transport or provider operation is admitted in this slice. Required legacy
capabilities remain migration work, including reads and their data ownership.
"""

from types import MappingProxyType

TOOL_MAPPING_VERSION = 1
# wire name -> (logical operation, intended effect class). Never permissions.
WIRE_TOOL_MAP = MappingProxyType(
    {
        "search_logs": ("siem.search_logs", "read"),
        "get_detections": ("detection.list_events", "read"),
        "get_incidents": ("ticketing.list_incidents", "read"),
        "create_incident": ("ticketing.create_incident", "write"),
        "list_playbooks": ("playbook.list", "read"),
        "get_playbook": ("playbook.get", "read"),
        "run_playbook": ("playbook.run", "write"),
        "get_playbook_execution": ("playbook.get_execution", "read"),
        "get_user": ("identity.get_user", "read"),
        "lock_account": ("identity.lock_account", "write"),
        "get_observable": ("observable.get", "read"),
        "search_observables": ("observable.search", "read"),
    }
)


class MCPToolUnavailable(PermissionError):
    """A source-only path has no verified caller/action/provider admission."""


UNAVAILABLE_MESSAGE = (
    "MCP tool execution is unavailable pending verified caller, tenant, "
    "capability and downstream action admission"
)


def require_tool_admission(tool_name, tenant_id=None, user_id=None, params=None):
    """Reject before credentials, clients, data access or effects.

    Strings, environment variables, UUID syntax, model/body claims and local
    approval/audit flags never establish caller or action authority. This is
    intentionally not a constructor for a trusted context or an allow list.
    Unknown operations are denied too. No caller values are logged or echoed.
    """
    raise MCPToolUnavailable(UNAVAILABLE_MESSAGE)
