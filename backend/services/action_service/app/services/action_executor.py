"""Legacy callable shapes retained; no request flag or placeholder grants execution."""

from fastapi import HTTPException


class ActionStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionExecutor:
    def _unavailable(self):
        raise HTTPException(
            503,
            "Legacy action execution requires qualified case authority and domain admission",
        )

    async def execute_action(
        self,
        action_type,
        action_params,
        ticket_id=None,
        tenant_id=None,
        user_id=None,
        requires_approval=None,
    ):
        self._unavailable()

    async def _execute_iam_action(self, *args, **kwargs):
        self._unavailable()

    async def _execute_endpoint_action(self, *args, **kwargs):
        self._unavailable()

    async def _execute_network_action(self, *args, **kwargs):
        self._unavailable()

    async def _execute_email_action(self, *args, **kwargs):
        self._unavailable()

    async def _execute_cloud_action(self, *args, **kwargs):
        self._unavailable()

    async def _update_ticket_with_action(self, *args, **kwargs):
        self._unavailable()
