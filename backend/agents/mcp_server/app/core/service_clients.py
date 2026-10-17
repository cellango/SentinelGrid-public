"""Unavailable legacy service-client surface; no eager credential/client setup.

A future gateway transport must bind owned configuration and verified caller
capabilities to an admitted domain client. Raw clients and tenant headers are
not a way around tool authorization or the IAM source-review restrictions.
"""

from app.core.tool_admission import require_tool_admission


class ServiceClients:
    SERVICE_NAMES = frozenset(
        {
            "siem_agent",
            "soar_agent",
            "iam_agent",
            "posture_agent",
            "observables_service",
            "detection_service",
            "compliance_service",
            "vulnerability_service",
            "ticketing_agent",
            "framework_service",
        }
    )

    def __getattr__(self, name):
        if name in self.SERVICE_NAMES:
            require_tool_admission(name)
        raise AttributeError(name)

    def add_tenant_header(self, tenant_id):
        require_tool_admission("legacy_tenant_header", tenant_id)

    async def close_all(self):
        # Nothing was constructed; importing this module creates no clients.
        return None


clients = ServiceClients()
