"""Playbook executor -- replaces n8n stubs with real HTTP-based workflow execution.

A playbook is a JSON structure containing *phases*, each with ordered *steps*.
Each step declares an ``action_type`` and ``parameters``.  The executor walks
through phases sequentially, calling the appropriate internal service endpoint
for each step.

Supported action types
----------------------
lock_account       - Lock a user account via IAM agent
disable_user       - Disable a user account via IAM agent
search_logs        - Search logs via SIEM agent
create_incident    - Create an incident via SOAR agent
update_incident    - Update incident status / severity
block_ip           - Block an IP via firewall API
quarantine_email   - Quarantine an email via email gateway
send_notification  - Send an alert notification (email / webhook / Slack)
enrich_ioc         - Look up an IOC in threat intelligence
wait_for_approval  - Pause and wait for human approval
run_sub_playbook   - Execute another playbook (recursive)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_TIMEOUT = 30.0  # seconds per HTTP call
_APPROVAL_POLL_INTERVAL = int(os.getenv("APPROVAL_POLL_INTERVAL", "15"))  # seconds
_APPROVAL_MAX_WAIT = int(os.getenv("APPROVAL_MAX_WAIT", "3600"))  # 1 hour
_TEMPLATE_RE = re.compile(r"\{\{(\s*[\w.]+\s*)\}\}")

# Type alias for step handlers
StepHandler = Callable[[Dict[str, Any], Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]


class PlaybookExecutor:
    """Executes playbook workflows by calling internal service endpoints."""

    def __init__(
        self,
        tenant_id: str,
        service_clients: Dict[str, str],
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        internal_token: Optional[str] = None,
    ) -> None:
        """
        Parameters
        ----------
        tenant_id:
            The tenant scope for all operations.
        service_clients:
            Mapping of service name to base URL, e.g.
            ``{"iam_agent": "http://iam_agent:8000", ...}``
        timeout:
            Default HTTP timeout in seconds.
        internal_token:
            Internal service-to-service bearer token.
        """
        self.tenant_id = tenant_id
        self.service_clients = service_clients
        self.timeout = timeout
        resolved_internal_token = internal_token or os.getenv("INTERNAL_SERVICE_TOKEN")
        if not resolved_internal_token:
            raise ValueError("INTERNAL_SERVICE_TOKEN must be configured for playbook execution")
        self.internal_token = resolved_internal_token

        # Map action_type -> handler method
        self._handlers: Dict[str, StepHandler] = {
            "lock_account": self._handle_lock_account,
            "disable_user": self._handle_disable_user,
            "search_logs": self._handle_search_logs,
            "create_incident": self._handle_create_incident,
            "update_incident": self._handle_update_incident,
            "block_ip": self._handle_block_ip,
            "quarantine_email": self._handle_quarantine_email,
            "send_notification": self._handle_send_notification,
            "enrich_ioc": self._handle_enrich_ioc,
            "wait_for_approval": self._handle_wait_for_approval,
            "run_sub_playbook": self._handle_run_sub_playbook,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(self, playbook: dict, context: dict) -> dict:
        """Execute a full playbook definition.

        Parameters
        ----------
        playbook:
            Playbook definition dict with ``phases`` (list of phase dicts)
            or ``workflow`` (React-Flow-style graph -- phases extracted).
        context:
            Runtime context (alert_id, incident_id, user_id, etc.).

        Returns
        -------
        dict
            Execution result with per-phase / per-step outcomes.
        """
        playbook_id = playbook.get("id", "unknown")
        playbook_name = playbook.get("name", "unnamed")
        phases = self._extract_phases(playbook)

        logger.info(
            "Playbook execution started: id=%s name=%s phases=%d tenant=%s",
            playbook_id,
            playbook_name,
            len(phases),
            self.tenant_id,
        )

        execution_start = time.monotonic()
        phase_results: List[dict] = []
        steps_completed = 0
        steps_failed = 0
        overall_status = "completed"

        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=self._auth_headers(),
        ) as client:
            self._client = client

            for phase_idx, phase in enumerate(phases):
                phase_name = phase.get("name", f"phase_{phase_idx}")
                steps = phase.get("steps", [])

                logger.info(
                    "Phase %d/%d started: %s (%d steps)",
                    phase_idx + 1,
                    len(phases),
                    phase_name,
                    len(steps),
                )

                phase_result = {
                    "phase": phase_name,
                    "phase_index": phase_idx,
                    "steps": [],
                    "status": "completed",
                }

                for step_idx, step in enumerate(steps):
                    step_result = await self._execute_step(step, context)
                    phase_result["steps"].append(step_result)

                    if step_result["status"] == "success":
                        steps_completed += 1
                        # Merge step output into context for downstream steps
                        step_output = step_result.get("output", {})
                        if isinstance(step_output, dict):
                            context.update(step_output)
                    else:
                        steps_failed += 1
                        on_failure = step.get("on_failure", "stop")
                        if on_failure == "stop":
                            phase_result["status"] = "failed"
                            overall_status = "failed"
                            logger.error(
                                "Step %d/%d in phase '%s' failed; stopping playbook.",
                                step_idx + 1,
                                len(steps),
                                phase_name,
                            )
                            break
                        # on_failure == "continue" -> keep going
                        logger.warning(
                            "Step %d/%d in phase '%s' failed; continuing (on_failure=continue).",
                            step_idx + 1,
                            len(steps),
                            phase_name,
                        )

                phase_results.append(phase_result)

                if overall_status == "failed":
                    break

            self._client = None  # type: ignore[assignment]

        elapsed = round(time.monotonic() - execution_start, 2)
        result = {
            "status": overall_status,
            "playbook_id": playbook_id,
            "playbook_name": playbook_name,
            "phases": phase_results,
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "elapsed_seconds": elapsed,
        }

        logger.info(
            "Playbook execution finished: id=%s status=%s completed=%d failed=%d elapsed=%.2fs",
            playbook_id,
            overall_status,
            steps_completed,
            steps_failed,
            elapsed,
        )
        return result

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------

    async def _execute_step(self, step: dict, context: dict) -> dict:
        """Execute a single playbook step.

        Returns a dict with ``status``, ``action_type``, ``output``, and
        optionally ``error``.
        """
        action_type = step.get("action_type", "unknown")
        step_name = step.get("name", action_type)
        params = step.get("parameters", {})
        params = self._resolve_params(params, context)

        logger.info("Step started: %s (action=%s)", step_name, action_type)
        start = time.monotonic()

        handler = self._handlers.get(action_type)
        if handler is None:
            error = f"Unknown action_type: {action_type}"
            logger.error(error)
            return {
                "name": step_name,
                "action_type": action_type,
                "status": "failed",
                "error": error,
                "elapsed_seconds": 0,
            }

        try:
            output = await handler(params, context)
            elapsed = round(time.monotonic() - start, 3)
            logger.info(
                "Step completed: %s elapsed=%.3fs", step_name, elapsed
            )
            return {
                "name": step_name,
                "action_type": action_type,
                "status": "success",
                "output": output,
                "elapsed_seconds": elapsed,
            }
        except Exception as exc:
            elapsed = round(time.monotonic() - start, 3)
            logger.exception(
                "Step failed: %s error=%s elapsed=%.3fs",
                step_name,
                exc,
                elapsed,
            )
            return {
                "name": step_name,
                "action_type": action_type,
                "status": "failed",
                "error": str(exc),
                "elapsed_seconds": elapsed,
            }

    # ------------------------------------------------------------------
    # Template resolution
    # ------------------------------------------------------------------

    def _resolve_params(self, params: dict, context: dict) -> dict:
        """Replace ``{{variable}}`` placeholders with context values.

        Supports dotted paths like ``{{alert.source_ip}}``.
        """
        resolved: Dict[str, Any] = {}
        for key, value in params.items():
            if isinstance(value, str):
                resolved[key] = _TEMPLATE_RE.sub(
                    lambda m: str(self._resolve_path(m.group(1).strip(), context)),
                    value,
                )
            elif isinstance(value, dict):
                resolved[key] = self._resolve_params(value, context)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_params(v, context) if isinstance(v, dict)
                    else _TEMPLATE_RE.sub(
                        lambda m: str(self._resolve_path(m.group(1).strip(), context)),
                        v,
                    ) if isinstance(v, str)
                    else v
                    for v in value
                ]
            else:
                resolved[key] = value
        return resolved

    @staticmethod
    def _resolve_path(path: str, context: dict) -> Any:
        """Resolve a dotted path against the context dict."""
        parts = path.split(".")
        current: Any = context
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, f"{{{{{path}}}}}")
            else:
                return f"{{{{{path}}}}}"
        return current

    # ------------------------------------------------------------------
    # Phase extraction
    # ------------------------------------------------------------------

    def _extract_phases(self, playbook: dict) -> List[dict]:
        """Extract an ordered list of phases from the playbook definition.

        Supports two formats:
        - ``phases``: a list of ``{name, steps: [...]}`` dicts (preferred).
        - ``workflow``: React-Flow graph with nodes/edges -- converted to
          a linear phase list.
        """
        phases = playbook.get("phases")
        if phases and isinstance(phases, list):
            return phases

        # Fallback: convert React-Flow workflow to linear phases
        workflow = playbook.get("workflow", {})
        nodes = workflow.get("nodes", [])
        if not nodes:
            logger.warning("Playbook has no phases and no workflow nodes")
            return []

        # Group nodes by their ``phase`` data attribute, or treat all as one phase
        phase_map: Dict[str, List[dict]] = {}
        for node in nodes:
            data = node.get("data", {})
            phase_name = data.get("phase", "default")
            step = {
                "name": data.get("label", node.get("id", "step")),
                "action_type": data.get("action_type", "unknown"),
                "parameters": data.get("parameters", {}),
                "on_failure": data.get("on_failure", "stop"),
            }
            phase_map.setdefault(phase_name, []).append(step)

        return [
            {"name": name, "steps": steps}
            for name, steps in phase_map.items()
        ]

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.internal_token}",
            "X-Tenant-ID": self.tenant_id,
            "Content-Type": "application/json",
        }

    def _url(self, service: str, path: str) -> str:
        base = self.service_clients.get(service, "")
        return f"{base.rstrip('/')}/{path.lstrip('/')}"

    # ==================================================================
    # Action handlers
    # ==================================================================

    async def _handle_lock_account(self, params: dict, context: dict) -> dict:
        """Lock a user account via IAM agent.

        Expected params: ``user_id``, optional ``reason``.
        """
        user_id = params["user_id"]
        reason = params.get("reason", "Automated playbook action")
        url = self._url("iam_agent", f"internal/iam/users/{user_id}/lock")

        resp = await self._client.post(url, json={"reason": reason})
        resp.raise_for_status()
        logger.info("Locked account for user %s", user_id)
        return {"user_id": user_id, "locked": True, "status_code": resp.status_code}

    async def _handle_disable_user(self, params: dict, context: dict) -> dict:
        """Disable a user account via IAM agent.

        Expected params: ``user_id``, optional ``reason``.
        """
        user_id = params["user_id"]
        reason = params.get("reason", "Automated playbook action")
        url = self._url("iam_agent", f"internal/iam/users/{user_id}/disable")

        resp = await self._client.post(url, json={"reason": reason})
        resp.raise_for_status()
        logger.info("Disabled user %s", user_id)
        return {"user_id": user_id, "disabled": True, "status_code": resp.status_code}

    async def _handle_search_logs(self, params: dict, context: dict) -> dict:
        """Search logs via SIEM agent.

        Expected params: ``query``, optional ``time_range``, ``limit``.
        """
        url = self._url("siem_agent", "api/v1/logs/search")
        payload = {
            "query": params.get("query", "*"),
            "time_range": params.get("time_range", "24h"),
            "limit": params.get("limit", 100),
        }

        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", [])
        logger.info("Log search returned %d hits", len(hits))
        return {"hits_count": len(hits), "hits": hits[:50]}

    async def _handle_create_incident(self, params: dict, context: dict) -> dict:
        """Create an incident via SOAR agent.

        Expected params: ``title``, ``severity``, optional ``description``,
        ``assignee``, ``category``.
        """
        url = self._url("soar_agent", "api/v1/incidents")
        payload = {
            "title": params["title"],
            "severity": params.get("severity", "medium"),
            "description": params.get("description", ""),
            "assignee": params.get("assignee"),
            "category": params.get("category"),
            "tenant_id": self.tenant_id,
        }

        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        incident = resp.json()
        incident_id = incident.get("id")
        logger.info("Created incident %s", incident_id)
        return {"incident_id": incident_id, "status_code": resp.status_code}

    async def _handle_update_incident(self, params: dict, context: dict) -> dict:
        """Update an existing incident.

        Expected params: ``incident_id``, and any of ``status``, ``severity``,
        ``assignee``, ``notes``.
        """
        incident_id = params["incident_id"]
        url = self._url("soar_agent", f"api/v1/incidents/{incident_id}")
        payload = {
            k: v
            for k, v in params.items()
            if k in ("status", "severity", "assignee", "notes") and v is not None
        }

        resp = await self._client.patch(url, json=payload)
        resp.raise_for_status()
        logger.info("Updated incident %s", incident_id)
        return {"incident_id": incident_id, "updated": True, "status_code": resp.status_code}

    async def _handle_block_ip(self, params: dict, context: dict) -> dict:
        """Block an IP address via firewall / network agent.

        Expected params: ``ip_address``, optional ``duration``, ``reason``.
        """
        ip_address = params["ip_address"]
        # The firewall endpoint is configurable; falls back to soar_agent
        firewall_url = os.getenv("FIREWALL_API_URL", self.service_clients.get("soar_agent", ""))
        url = f"{firewall_url.rstrip('/')}/api/v1/firewall/block"
        payload = {
            "ip_address": ip_address,
            "duration": params.get("duration", "24h"),
            "reason": params.get("reason", "Automated playbook action"),
            "tenant_id": self.tenant_id,
        }

        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        logger.info("Blocked IP %s", ip_address)
        return {"ip_address": ip_address, "blocked": True, "status_code": resp.status_code}

    async def _handle_quarantine_email(self, params: dict, context: dict) -> dict:
        """Quarantine an email via email gateway.

        Expected params: ``message_id``, optional ``reason``.
        """
        message_id = params["message_id"]
        email_gw_url = os.getenv(
            "EMAIL_GATEWAY_URL",
            self.service_clients.get("soar_agent", ""),
        )
        url = f"{email_gw_url.rstrip('/')}/api/v1/email/quarantine"
        payload = {
            "message_id": message_id,
            "reason": params.get("reason", "Automated playbook action"),
            "tenant_id": self.tenant_id,
        }

        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        logger.info("Quarantined email %s", message_id)
        return {"message_id": message_id, "quarantined": True, "status_code": resp.status_code}

    async def _handle_send_notification(self, params: dict, context: dict) -> dict:
        """Send a notification (email, webhook, or Slack).

        Expected params: ``channel`` (email|webhook|slack), ``recipients``,
        ``subject``, ``body``.
        """
        channel = params.get("channel", "email")
        url = self._url("soar_agent", "api/v1/notifications/send")
        payload = {
            "channel": channel,
            "recipients": params.get("recipients", []),
            "subject": params.get("subject", "SentinelGrid Alert"),
            "body": params.get("body", ""),
            "tenant_id": self.tenant_id,
        }

        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        logger.info("Notification sent via %s to %s", channel, payload["recipients"])
        return {"channel": channel, "sent": True, "status_code": resp.status_code}

    async def _handle_enrich_ioc(self, params: dict, context: dict) -> dict:
        """Enrich an IOC with threat intelligence.

        Expected params: ``ioc_type`` (ip|domain|hash|url), ``ioc_value``.
        """
        ioc_type = params.get("ioc_type", "ip")
        ioc_value = params["ioc_value"]
        url = self._url("siem_agent", "api/v1/threat-intel/enrich")
        payload = {
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "tenant_id": self.tenant_id,
        }

        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        enrichment = resp.json()
        logger.info("Enriched IOC %s=%s", ioc_type, ioc_value)
        return {"ioc_type": ioc_type, "ioc_value": ioc_value, "enrichment": enrichment}

    async def _handle_wait_for_approval(self, params: dict, context: dict) -> dict:
        """Pause execution and wait for human approval.

        Creates an approval request and polls until approved, denied, or timed out.

        Expected params: ``approver`` (user or group), optional ``message``,
        ``timeout_seconds``.
        """
        approver = params.get("approver", "security-team")
        message = params.get("message", "Playbook step requires approval")
        max_wait = int(params.get("timeout_seconds", _APPROVAL_MAX_WAIT))

        # Create approval request
        url = self._url("soar_agent", "api/v1/approvals")
        resp = await self._client.post(
            url,
            json={
                "approver": approver,
                "message": message,
                "tenant_id": self.tenant_id,
                "context": {k: str(v) for k, v in context.items() if isinstance(v, (str, int, float, bool))},
            },
        )
        resp.raise_for_status()
        approval = resp.json()
        approval_id = approval.get("id", "unknown")

        logger.info(
            "Waiting for approval %s from %s (max %ds)",
            approval_id,
            approver,
            max_wait,
        )

        # Poll for approval status
        poll_url = self._url("soar_agent", f"api/v1/approvals/{approval_id}")
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(_APPROVAL_POLL_INTERVAL)
            waited += _APPROVAL_POLL_INTERVAL

            poll_resp = await self._client.get(poll_url)
            if poll_resp.status_code == 200:
                status_data = poll_resp.json()
                decision = status_data.get("status")
                if decision == "approved":
                    logger.info("Approval %s granted", approval_id)
                    return {"approval_id": approval_id, "decision": "approved"}
                elif decision == "denied":
                    raise RuntimeError(
                        f"Approval {approval_id} denied by {status_data.get('decided_by', 'unknown')}"
                    )

        raise TimeoutError(
            f"Approval {approval_id} timed out after {max_wait}s"
        )

    async def _handle_run_sub_playbook(self, params: dict, context: dict) -> dict:
        """Execute a sub-playbook by submitting a new Celery task.

        Expected params: ``playbook_id``.  Optionally ``wait`` (bool, default False).
        """
        from sg_tasks.tasks import run_playbook_task

        sub_playbook_id = params["playbook_id"]
        wait = params.get("wait", False)

        # Submit Celery task
        result = run_playbook_task.delay(
            tenant_id=self.tenant_id,
            playbook_id=sub_playbook_id,
            execution_id=params.get("execution_id", "sub-exec"),
            context=context,
        )

        logger.info("Submitted sub-playbook %s (task_id=%s)", sub_playbook_id, result.id)

        if wait:
            # Block until sub-playbook completes (with timeout)
            timeout = int(params.get("timeout_seconds", 600))
            output = result.get(timeout=timeout)
            return {"sub_playbook_id": sub_playbook_id, "celery_task_id": result.id, "result": output}

        return {"sub_playbook_id": sub_playbook_id, "celery_task_id": result.id, "async": True}
