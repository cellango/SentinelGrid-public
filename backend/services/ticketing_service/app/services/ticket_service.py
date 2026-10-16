"""Main ticket service with enrichment integration."""

import logging
import asyncio
import os
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from datetime import datetime
from uuid import UUID
import httpx
import re

from sg_core.models import Ticket, Alert
from sg_events.workflow import (
    WorkflowEventType,
    WorkflowStage,
    publish_workflow_event,
)
from app.core.config import settings
from app.services.zammad_client import ZammadClient

logger = logging.getLogger(__name__)


@dataclass
class TicketingHandoffConfig:
    customer_managed: bool = False
    provider: str = "internal"
    url: Optional[str] = None
    project: Optional[str] = None
    api_key: Optional[str] = None
    issue_type: Optional[str] = None
    assignment_mode: str = "service_owner"
    default_assignee: Optional[str] = None
    assignee_identifier_type: str = "username"
    auto_create_tickets: bool = True
    notify_slack: bool = False
    slack_channel: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    health_status: Optional[str] = None


class TicketService:
    """Service for managing tickets with enrichment."""
    
    def __init__(self):
        self.enrichment_agent_url = settings.AI_ENRICHMENT_AGENT_URL
        self.framework_service_url = settings.FRAMEWORK_SERVICE_URL
        self.vuln_service_url = settings.VULNERABILITY_SERVICE_URL
        self.scanner_orchestrator_url = settings.SCANNER_ORCHESTRATOR_URL.rstrip("/")
        self.model_gateway_url = settings.MODEL_GATEWAY_URL.rstrip("/")
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
        self.ticketing_provider = settings.TICKETING_PROVIDER.lower()
        self.default_realm = os.getenv("REALM_NAME", "demo")
        pr_map = {}
        for part in (settings.ZAMMAD_PRIORITY_MAP or "").split(","):
            if ":" in part:
                k, v = part.split(":", 1)
                pr_map[k.strip().lower()] = v.strip()
        self.zammad = (
            ZammadClient(
                base_url=settings.ZAMMAD_URL,
                token=settings.ZAMMAD_TOKEN or "",
                group=settings.ZAMMAD_GROUP,
                priority_map=pr_map or {"low": "1", "medium": "2", "high": "3", "critical": "4"},
                verify_tls=settings.UPSTREAM_TLS_VERIFY,
            )
            if settings.ZAMMAD_URL and settings.ZAMMAD_TOKEN and self.ticketing_provider == "zammad"
            else None
        )

    def _workflow_id_for_ticket(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
    ) -> str:
        return str(ticket_data.get("workflow_id") or ticket_data.get("incident_id") or ticket.id)

    def _publish_workflow_event_safe(
        self,
        *,
        db: Session,
        tenant_id: Union[UUID, str],
        event_type: WorkflowEventType,
        stage: WorkflowStage,
        workflow_id: Union[UUID, str],
        title: str,
        resource_type: str,
        resource_id: Union[UUID, str],
        resource_name: Optional[str],
        related_resources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        try:
            publish_workflow_event(
                event_type=event_type,
                stage=stage,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                source_service="ticketing_service",
                title=title,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                related_resources=related_resources,
                metadata=metadata,
                success=success,
                error_message=error_message,
                db_session=db,
                realm_name=self.default_realm,
            )
        except Exception as workflow_err:
            logger.warning(
                "Failed to record workflow event %s for resource %s:%s: %s",
                event_type.value,
                resource_type,
                resource_id,
                workflow_err,
            )
    
    async def create_ticket(
        self,
        db: Session,
        tenant_id: Union[UUID, str],
        ticket_data: Dict[str, Any],
        handoff_config: Optional[TicketingHandoffConfig] = None,
    ) -> Ticket:
        """
        Create a new ticket with automatic enrichment.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            ticket_data: Ticket data dictionary
        
        Returns:
            Created Ticket object
        """
        handoff_config = handoff_config or self.resolve_handoff_config(db, tenant_id, ticket_data)

        # Create ticket
        tenant_slug = ticket_data.get("tenant_slug") or ticket_data.get("sg_tenant_slug")
        public_id = self._generate_public_id(tenant_slug)
        ticket = Ticket(
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            title=ticket_data["title"],
            description=ticket_data.get("description"),
            status=ticket_data.get("status", "open"),
            severity=ticket_data.get("severity"),
            priority=ticket_data.get("priority"),
            category=ticket_data.get("category"),
            source="internal",  # hide vendor; we expose SG branding
            external_id=public_id,
            cve_ids=ticket_data.get("cve_ids", []),
            exploit_indicators=ticket_data.get("exploit_indicators", {}),
            vm_data={"fix_group_id": ticket_data.get("fix_group_id"), "scan_id": ticket_data.get("scan_id")},
        )
        if ticket_data.get("assigned_to"):
            ticket.assigned_to = ticket_data.get("assigned_to")
        if ticket_data.get("due_date"):
            ticket.due_date = ticket_data.get("due_date")
        self._record_ticket_mutation_events(
            ticket,
            previous_status=None,
            previous_assignee=None,
            previous_due_date=None,
            ticket_data=ticket_data,
            created=True,
        )
        
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        # Link alerts if provided
        if ticket_data.get("alert_ids"):
            await self._link_alerts(db, ticket.id, ticket_data["alert_ids"], tenant_id)
        # Link to incident if provided
        if ticket_data.get("incident_id"):
            try:
                from sqlalchemy import text
                db.execute(
                    text("UPDATE incidents SET ticket_id=:ticket_id, external_ticket_id=:ext_id, external_ticket_provider=:provider WHERE id=:incident_id AND tenant_id=:tenant_id"),
                    {
                        "ticket_id": str(ticket.id),
                        "ext_id": ticket.external_id,
                        "provider": ticket.source,
                        "incident_id": ticket_data["incident_id"],
                        "tenant_id": str(tenant_id),
                    },
                )
                db.commit()
            except Exception as e:
                logger.error(f"Failed linking incident {ticket_data.get('incident_id')} to ticket {ticket.id}: {e}")

        # Link vulnerabilities if CVE IDs provided
        if ticket.cve_ids:
            await self._link_vulnerabilities(db, ticket.id, ticket.cve_ids, tenant_id)

        workflow_id = self._workflow_id_for_ticket(ticket, ticket_data)
        related_resources: List[Dict[str, Any]] = []
        if ticket_data.get("incident_id"):
            related_resources.append(
                {
                    "type": "incident",
                    "id": str(ticket_data["incident_id"]),
                    "title": ticket.title,
                }
            )
        for alert_id in ticket_data.get("alert_ids") or []:
            related_resources.append(
                {
                    "type": "alert",
                    "id": str(alert_id),
                }
            )

        self._publish_workflow_event_safe(
            db=db,
            tenant_id=tenant_id,
            event_type=WorkflowEventType.TICKET_CREATED,
            stage=WorkflowStage.TICKETING,
            workflow_id=workflow_id,
            title="SentinelGrid ticket created",
            resource_type="ticket",
            resource_id=ticket.id,
            resource_name=ticket.title,
            related_resources=related_resources,
            metadata={
                "ticket_id": str(ticket.id),
                "ticket_external_id": ticket.external_id,
                "severity": ticket.severity,
                "priority": ticket.priority,
                "category": ticket.category,
            },
        )
        if ticket_data.get("incident_id"):
            self._publish_workflow_event_safe(
                db=db,
                tenant_id=tenant_id,
                event_type=WorkflowEventType.TICKET_CREATED,
                stage=WorkflowStage.TICKETING,
                workflow_id=workflow_id,
                title="Ticket created for this incident",
                resource_type="incident",
                resource_id=ticket_data["incident_id"],
                resource_name=ticket.title,
                related_resources=[
                    {
                        "type": "ticket",
                        "id": str(ticket.id),
                        "title": ticket.title,
                    }
                ],
                metadata={
                    "ticket_id": str(ticket.id),
                    "ticket_external_id": ticket.external_id,
                    "severity": ticket.severity,
                    "priority": ticket.priority,
                },
            )

        # Create external ticket in Zammad if configured for SaaS-managed tenants only
        if not handoff_config.customer_managed and self.zammad and self.ticketing_provider == "zammad":
            payload = self.zammad.build_payload(
                title=ticket.title,
                description=ticket.description or ticket.title,
                severity=ticket.severity,
                tenant_id=str(tenant_id),
                alert_ids=ticket_data.get("alert_ids"),
                incident_id=ticket_data.get("incident_id"),
                custom={
                    "sg_severity": ticket.severity,
                    "sg_category": ticket.category,
                    "sg_incident_mode": ticket_data.get("incident_management_mode"),
                    "sg_public_id": public_id,
                },
            )
            z_ticket = await self.zammad.create_ticket(payload)
            if z_ticket and z_ticket.get("id"):
                # Keep SG public ID; store vendor id separately
                ticket.external_vendor_id = str(z_ticket["id"])
                ticket.timeline_data = self._annotate_external_provider(
                    ticket.timeline_data,
                    "zammad",
                )
                ticket.source = "internal"
                if ticket_data.get("incident_id"):
                    db.execute(
                        text(
                            """
                            UPDATE incidents
                            SET external_ticket_id = :external_id,
                                external_ticket_provider = :provider
                            WHERE id = :incident_id AND tenant_id = :tenant_id
                            """
                        ),
                        {
                            "external_id": str(z_ticket["id"]),
                            "provider": "zammad",
                            "incident_id": ticket_data["incident_id"],
                            "tenant_id": str(tenant_id),
                        },
                    )
                db.commit()
                db.refresh(ticket)
                self._publish_workflow_event_safe(
                    db=db,
                    tenant_id=tenant_id,
                    event_type=WorkflowEventType.TICKET_HANDOFF_COMPLETED,
                    stage=WorkflowStage.TICKETING,
                    workflow_id=workflow_id,
                    title="Zammad handoff created",
                    resource_type="incident" if ticket_data.get("incident_id") else "ticket",
                    resource_id=ticket_data.get("incident_id") or ticket.id,
                    resource_name=ticket.title,
                    related_resources=[
                        {
                            "type": "ticket",
                            "id": str(ticket.id),
                            "title": ticket.title,
                        }
                    ],
                    metadata={
                        "provider": "zammad",
                        "external_vendor_id": ticket.external_vendor_id,
                        "ticket_id": str(ticket.id),
                    },
                )
        elif handoff_config.customer_managed:
            await self._dispatch_customer_managed_handoff(
                db=db,
                tenant_id=tenant_id,
                ticket=ticket,
                ticket_data=ticket_data,
                config=handoff_config,
            )
        
        # Map to frameworks (async, non-blocking)
        asyncio.create_task(self._map_to_frameworks_async(ticket, tenant_id))
        
        # Trigger AI enrichment (async, non-blocking)
        asyncio.create_task(self._trigger_enrichment_async(ticket.id, tenant_id))
        asyncio.create_task(self._embed_ticket(tenant_id, ticket, ticket_data.get("assets") or []))
        
        return ticket

    def _generate_public_id(self, tenant_slug: Optional[str]) -> str:
        """Generate SG-prefixed ticket ID with tenant slug."""
        slug = (tenant_slug or "tenant").lower()
        slug = re.sub(r'[^a-z0-9-]', '-', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        if len(slug) < 3:
            slug = f"{slug}xxx"[:3]
        timestamp = int(datetime.utcnow().timestamp())
        return f"SG-{slug}-{timestamp}"

    def resolve_handoff_config(
        self,
        db: Session,
        tenant_id: Union[UUID, str],
        ticket_data: Optional[Dict[str, Any]] = None,
    ) -> TicketingHandoffConfig:
        """Resolve customer-managed handoff settings from tenant state and onboarding progress."""
        ticket_data = ticket_data or {}
        tenant_row = {}
        try:
            tenant_row = db.execute(
                text(
                    """
                    SELECT id, slug, customer_id, incident_management_mode, ticketing_provider, ticketing_project, services_selected
                    FROM tenants
                    WHERE id = :tenant_id
                    LIMIT 1
                    """
                ),
                {"tenant_id": str(tenant_id)},
            ).mappings().fetchone() or {}
        except Exception as exc:
            logger.warning("Failed to resolve tenant handoff context for tenant %s: %s", tenant_id, exc)

        tenant_services = tenant_row.get("services_selected") or {}
        customer_id = str(tenant_row.get("customer_id")) if tenant_row.get("customer_id") else None

        onboarding_row = {}
        try:
            onboarding_row = db.execute(
                text(
                    """
                    SELECT services_selected, ticketing_config, ticketing_health
                    FROM onboarding_progress
                    WHERE customer_id = :tenant_id
                       OR (:customer_id IS NOT NULL AND customer_id = :customer_id)
                    ORDER BY CASE WHEN customer_id = :tenant_id THEN 0 ELSE 1 END
                    LIMIT 1
                    """
                ),
                {"tenant_id": str(tenant_id), "customer_id": customer_id},
            ).mappings().fetchone() or {}
        except Exception as exc:
            logger.warning("Failed to resolve onboarding handoff settings for tenant %s: %s", tenant_id, exc)

        onboarding_services = onboarding_row.get("services_selected") or {}
        ticketing_config = onboarding_row.get("ticketing_config") or {}
        ticketing_health = onboarding_row.get("ticketing_health") or {}
        requested_mode = str(ticket_data.get("incident_management_mode") or "").lower()
        customer_managed = any(
            (
                requested_mode == "customer_managed",
                onboarding_services.get("socManaged") is False,
                tenant_services.get("socManaged") is False,
                tenant_row.get("incident_management_mode") == "customer_managed",
            )
        )

        provider = (
            ticketing_config.get("provider")
            or onboarding_services.get("ticketing")
            or ticket_data.get("ticketing_provider")
            or tenant_row.get("ticketing_provider")
            or "internal"
        )

        return TicketingHandoffConfig(
            customer_managed=customer_managed,
            provider=str(provider).lower(),
            url=ticketing_config.get("url"),
            project=ticketing_config.get("project") or tenant_row.get("ticketing_project"),
            api_key=ticketing_config.get("api_key"),
            issue_type=ticketing_config.get("issue_type") or self._default_issue_type(str(provider).lower()),
            assignment_mode=ticketing_config.get("assignment_mode") or "service_owner",
            default_assignee=ticketing_config.get("default_assignee"),
            assignee_identifier_type=(
                ticketing_config.get("assignee_identifier_type")
                or self._default_assignee_identifier_type(str(provider).lower())
            ),
            auto_create_tickets=bool(ticketing_config.get("auto_create_tickets", provider != "internal")),
            notify_slack=bool(ticketing_config.get("notify_slack")),
            slack_channel=ticketing_config.get("slack_channel"),
            slack_webhook_url=ticketing_config.get("slack_webhook_url"),
            health_status=ticketing_health.get("status"),
        )

    def _default_issue_type(self, provider: str) -> str:
        if provider == "servicenow":
            return "Security Incident"
        return "Incident"

    def _default_assignee_identifier_type(self, provider: str) -> str:
        normalized = (provider or "internal").lower()
        if normalized == "jira":
            return "account_id"
        if normalized == "servicenow":
            return "username"
        return "username"

    def _build_auth_headers(self, api_key: Optional[str]) -> Dict[str, str]:
        token = (api_key or "").strip()
        if not token:
            return {}
        if re.match(r"^(basic|bearer)\s+", token, re.IGNORECASE):
            return {"Authorization": token}
        return {"Authorization": f"Bearer {token}"}

    def _routing_hint(self, config: TicketingHandoffConfig) -> str:
        if config.assignment_mode == "named_owner":
            return f"Assign to {config.default_assignee or 'named owner'}."
        if config.assignment_mode == "project_default":
            return "Use the downstream project or assignment-group defaults."
        return "Route based on the mapped service owner."

    def _build_external_ticket_description(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
    ) -> str:
        lines = [ticket.description or ticket.title, "", "SentinelGrid context:"]
        lines.append(f"- SG ticket ID: {ticket.external_id}")
        lines.append(f"- Severity: {ticket.severity or 'unknown'}")
        if ticket.category:
            lines.append(f"- Category: {ticket.category}")
        if ticket_data.get("incident_id"):
            lines.append(f"- SentinelGrid incident: {ticket_data['incident_id']}")
        if ticket_data.get("alert_ids"):
            lines.append(f"- Alerts: {', '.join(ticket_data['alert_ids'][:5])}")
        lines.append(f"- Routing: {self._routing_hint(config)}")
        return "\n".join(lines)

    def _resolve_external_assignee(
        self,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
    ) -> Optional[str]:
        if ticket_data.get("assigned_to"):
            return str(ticket_data["assigned_to"])
        if config.assignment_mode == "named_owner" and config.default_assignee:
            return str(config.default_assignee)
        return None

    def _build_jira_assignee_field(
        self,
        identifier: Optional[str],
        identifier_type: str,
    ) -> Optional[Dict[str, str]]:
        if not identifier:
            return None
        normalized = (identifier_type or "account_id").lower()
        if normalized == "email":
            return {"emailAddress": identifier}
        if normalized == "username":
            return {"name": identifier}
        return {"accountId": identifier}

    def _annotate_external_provider(
        self,
        timeline_data: Optional[Dict[str, Any]],
        provider: str,
    ) -> Dict[str, Any]:
        next_timeline = dict(timeline_data or {})
        next_timeline["external_ticket_provider"] = provider
        return next_timeline

    def _append_timeline_event(
        self,
        timeline_data: Optional[Dict[str, Any]],
        event_type: str,
        title: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        next_timeline = dict(timeline_data or {})
        events = list(next_timeline.get("events") or [])
        events.append(
            {
                "ts": datetime.utcnow().isoformat(),
                "type": event_type,
                "title": title,
                "metadata": metadata or {},
            }
        )
        next_timeline["events"] = events[-25:]
        return next_timeline

    def _append_comment_event(
        self,
        timeline_data: Optional[Dict[str, Any]],
        comment: str,
        actor: str = "operator",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        next_timeline = dict(timeline_data or {})
        events = list(next_timeline.get("events") or [])
        events.append(
            {
                "ts": datetime.utcnow().isoformat(),
                "type": "comment",
                "title": "Comment added",
                "text": comment,
                "description": comment,
                "actor": actor,
                "metadata": metadata or {},
            }
        )
        next_timeline["events"] = events[-25:]
        return next_timeline

    def _record_ticket_mutation_events(
        self,
        ticket: Ticket,
        previous_status: Optional[str],
        previous_assignee: Optional[str],
        previous_due_date: Optional[str],
        ticket_data: Dict[str, Any],
        *,
        created: bool = False,
    ) -> None:
        """Append timeline entries for lifecycle, status, and assignment changes."""
        if created:
            ticket.timeline_data = self._append_timeline_event(
                ticket.timeline_data,
                "ticket_created",
                "SentinelGrid ticket created",
                {
                    "status": ticket.status,
                    "severity": ticket.severity,
                    "priority": ticket.priority,
                },
            )

        if "status" in ticket_data and ticket.status != previous_status:
            ticket.timeline_data = self._append_timeline_event(
                ticket.timeline_data,
                "status_updated",
                f"Status changed to {ticket.status}",
                {
                    "previous_status": previous_status,
                    "status": ticket.status,
                },
            )

        current_assignee = getattr(ticket, "assigned_to", None)
        if "assigned_to" in ticket_data and current_assignee != previous_assignee:
            ticket.timeline_data = self._append_timeline_event(
                ticket.timeline_data,
                "assignment_updated",
                f"Assigned to {current_assignee or 'unassigned'}",
                {
                    "previous_assigned_to": previous_assignee,
                    "assigned_to": current_assignee,
                },
            )

        current_due_date = getattr(ticket, "due_date", None)
        if "due_date" in ticket_data and current_due_date != previous_due_date:
            ticket.timeline_data = self._append_timeline_event(
                ticket.timeline_data,
                "sla_updated",
                f"SLA target set to {current_due_date or 'unset'}",
                {
                    "previous_due_date": previous_due_date,
                    "due_date": current_due_date,
                },
            )

    async def _dispatch_customer_managed_handoff(
        self,
        db: Session,
        tenant_id: Union[UUID, str],
        ticket: Ticket,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
    ) -> None:
        external_result: Optional[Dict[str, Any]] = None
        workflow_id = self._workflow_id_for_ticket(ticket, ticket_data)
        target_resource_type = "incident" if ticket_data.get("incident_id") else "ticket"
        target_resource_id = ticket_data.get("incident_id") or ticket.id
        target_related_resources = [
            {
                "type": "ticket",
                "id": str(ticket.id),
                "title": ticket.title,
            }
        ]

        try:
            if config.auto_create_tickets and config.provider in {"jira", "servicenow"} and config.url and config.project and config.api_key:
                if config.provider == "jira":
                    external_result = await self._create_jira_issue(ticket, ticket_data, config)
                else:
                    external_result = await self._create_servicenow_incident(ticket, ticket_data, config)

                if external_result and external_result.get("external_id"):
                    ticket.external_vendor_id = str(external_result["external_id"])
                    ticket.timeline_data = self._annotate_external_provider(
                        ticket.timeline_data,
                        config.provider,
                    )
                    ticket.timeline_data = self._append_timeline_event(
                        ticket.timeline_data,
                        "external_ticket_created",
                        f"{config.provider.title()} handoff created",
                        {
                            "provider": config.provider,
                            "external_id": external_result["external_id"],
                            "project": config.project,
                        },
                    )
                    if ticket_data.get("incident_id"):
                        db.execute(
                            text(
                                """
                                UPDATE incidents
                                SET external_ticket_id = :external_id,
                                    external_ticket_provider = :provider
                                WHERE id = :incident_id AND tenant_id = :tenant_id
                                """
                            ),
                            {
                                "external_id": str(external_result["external_id"]),
                                "provider": config.provider,
                                "incident_id": ticket_data["incident_id"],
                                "tenant_id": str(tenant_id),
                            },
                    )
                db.commit()
                db.refresh(ticket)
                self._publish_workflow_event_safe(
                    db=db,
                    tenant_id=tenant_id,
                    event_type=WorkflowEventType.TICKET_HANDOFF_COMPLETED,
                    stage=WorkflowStage.TICKETING,
                    workflow_id=workflow_id,
                    title=f"{config.provider.title()} handoff created",
                    resource_type=target_resource_type,
                    resource_id=target_resource_id,
                    resource_name=ticket.title,
                    related_resources=target_related_resources,
                    metadata={
                        "provider": config.provider,
                        "external_id": external_result.get("external_id") if external_result else None,
                        "project": config.project,
                        "ticket_id": str(ticket.id),
                    },
                )
            elif config.customer_managed:
                ticket.timeline_data = self._append_timeline_event(
                    ticket.timeline_data,
                    "external_ticket_skipped",
                    "Customer-managed handoff saved without automatic downstream ticket creation",
                    {
                        "provider": config.provider,
                        "auto_create_tickets": config.auto_create_tickets,
                    },
                )
                db.commit()
                db.refresh(ticket)
                self._publish_workflow_event_safe(
                    db=db,
                    tenant_id=tenant_id,
                    event_type=WorkflowEventType.TICKET_HANDOFF_SKIPPED,
                    stage=WorkflowStage.TICKETING,
                    workflow_id=workflow_id,
                    title="Customer-managed handoff saved without downstream ticket creation",
                    resource_type=target_resource_type,
                    resource_id=target_resource_id,
                    resource_name=ticket.title,
                    related_resources=target_related_resources,
                    metadata={
                        "provider": config.provider,
                        "auto_create_tickets": config.auto_create_tickets,
                        "ticket_id": str(ticket.id),
                    },
                )

            if config.notify_slack and config.slack_webhook_url:
                await self._send_slack_handoff(ticket, ticket_data, config, external_result)
                ticket.timeline_data = self._append_timeline_event(
                    ticket.timeline_data,
                    "slack_notification_sent",
                    "Slack handoff notification sent",
                    {
                        "channel": config.slack_channel,
                        "provider": config.provider,
                    },
                )
                db.commit()
                db.refresh(ticket)
                self._publish_workflow_event_safe(
                    db=db,
                    tenant_id=tenant_id,
                    event_type=WorkflowEventType.NOTIFICATION_SENT,
                    stage=WorkflowStage.NOTIFICATION,
                    workflow_id=workflow_id,
                    title="Workflow notification sent",
                    resource_type=target_resource_type,
                    resource_id=target_resource_id,
                    resource_name=ticket.title,
                    related_resources=target_related_resources,
                    metadata={
                        "provider": config.provider,
                        "channel": config.slack_channel,
                        "ticket_id": str(ticket.id),
                        "external_id": external_result.get("external_id") if external_result else None,
                    },
                )
        except Exception as exc:
            logger.warning("Customer-managed handoff failed for ticket %s: %s", ticket.id, exc)
            ticket.timeline_data = self._append_timeline_event(
                ticket.timeline_data,
                "external_ticket_failed",
                "Customer-managed handoff failed",
                {
                    "provider": config.provider,
                    "error": str(exc),
                },
            )
            db.commit()
            db.refresh(ticket)
            self._publish_workflow_event_safe(
                db=db,
                tenant_id=tenant_id,
                event_type=WorkflowEventType.WORKFLOW_FAILED,
                stage=WorkflowStage.TICKETING,
                workflow_id=workflow_id,
                title="Customer-managed handoff failed",
                resource_type=target_resource_type,
                resource_id=target_resource_id,
                resource_name=ticket.title,
                related_resources=target_related_resources,
                metadata={
                    "provider": config.provider,
                    "ticket_id": str(ticket.id),
                    "error": str(exc),
                },
                success=False,
                error_message=str(exc),
            )

    async def _create_jira_issue(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
    ) -> Dict[str, Any]:
        payload = {
            "fields": {
                "project": {"key": config.project},
                "summary": f"[SentinelGrid] {ticket.title}",
                "description": self._build_external_ticket_description(ticket, ticket_data, config),
                "issuetype": {"name": config.issue_type or self._default_issue_type("jira")},
                "labels": ["sentinelgrid", (ticket.severity or "unknown").lower()],
            }
        }
        assignee_field = self._build_jira_assignee_field(
            self._resolve_external_assignee(ticket_data, config),
            config.assignee_identifier_type,
        )
        if assignee_field:
            payload["fields"]["assignee"] = assignee_field
        priority_name = self._map_priority_to_jira(ticket.priority or ticket.severity)
        if priority_name:
            payload["fields"]["priority"] = {"name": priority_name}

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._build_auth_headers(config.api_key),
        }
        url = f"{config.url.rstrip('/')}/rest/api/2/issue"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return {
            "provider": "jira",
            "external_id": data.get("key") or data.get("id"),
            "response": data,
        }

    async def _create_servicenow_incident(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
    ) -> Dict[str, Any]:
        severity = (ticket.severity or "medium").lower()
        payload = {
            "short_description": f"[SentinelGrid] {ticket.title}",
            "description": self._build_external_ticket_description(ticket, ticket_data, config),
            "category": "security",
            "subcategory": ticket.category or "security_alert",
            "assignment_group": config.project,
            "severity": self._map_severity_to_servicenow(severity),
            "urgency": self._map_severity_to_servicenow(severity),
            "impact": self._map_severity_to_servicenow(severity),
        }
        resolved_assignee = self._resolve_external_assignee(ticket_data, config)
        if config.assignment_mode == "named_owner" and resolved_assignee:
            payload["assigned_to"] = resolved_assignee

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._build_auth_headers(config.api_key),
        }
        url = f"{config.url.rstrip('/')}/api/now/table/incident"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        result = data.get("result") or {}
        return {
            "provider": "servicenow",
            "external_id": result.get("number") or result.get("sys_id"),
            "response": data,
        }

    async def _send_slack_handoff(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
        external_result: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not config.slack_webhook_url:
            return
        body = {
            "channel": config.slack_channel,
            "text": f"SentinelGrid incident handoff: {ticket.title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*SentinelGrid incident handoff*\n*{ticket.title}*",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*SG Ticket*\n{ticket.external_id}"},
                        {"type": "mrkdwn", "text": f"*Severity*\n{ticket.severity or 'unknown'}"},
                        {"type": "mrkdwn", "text": f"*Provider*\n{config.provider.title()}"},
                        {"type": "mrkdwn", "text": f"*Routing*\n{self._routing_hint(config)}"},
                    ],
                },
            ],
        }
        if external_result and external_result.get("external_id"):
            body["blocks"].append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Downstream ticket*: `{external_result['external_id']}`",
                    },
                }
            )
        if ticket_data.get("incident_id"):
            body["blocks"].append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Incident ID*: `{ticket_data['incident_id']}`",
                    },
                }
            )
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(config.slack_webhook_url, json=body)
            response.raise_for_status()

    def _map_priority_to_jira(self, value: Optional[str]) -> Optional[str]:
        mapping = {
            "p1": "Highest",
            "p2": "High",
            "p3": "Medium",
            "p4": "Low",
            "critical": "Highest",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        }
        return mapping.get((value or "").lower())

    def _map_severity_to_servicenow(self, severity: str) -> str:
        mapping = {
            "critical": "1",
            "high": "2",
            "medium": "3",
            "low": "4",
        }
        return mapping.get(severity, "3")

    def _desired_jira_transition_names(self, status: str) -> List[str]:
        normalized = (status or "").lower()
        mapping = {
            "open": ["Open", "To Do", "Todo", "Backlog", "Selected for Development"],
            "in_progress": ["In Progress", "Investigating", "Doing", "In Review"],
            "resolved": ["Resolved", "Done", "Complete", "Completed"],
            "closed": ["Closed", "Done", "Resolved", "Complete", "Completed"],
        }
        return mapping.get(normalized, [status])

    def _pick_jira_transition_id(
        self,
        transitions: List[Dict[str, Any]],
        status: str,
    ) -> Optional[str]:
        desired = [name.lower() for name in self._desired_jira_transition_names(status)]
        for transition in transitions:
            target = ((transition.get("to") or {}).get("name") or "").lower()
            if target in desired:
                return transition.get("id")
        return None

    def _map_status_to_servicenow_state(self, status: str) -> str:
        mapping = {
            "open": "1",
            "in_progress": "2",
            "resolved": "6",
            "closed": "7",
        }
        return mapping.get((status or "").lower(), "2")

    def _build_jira_update_fields(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
    ) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        if "title" in ticket_data:
            fields["summary"] = f"[SentinelGrid] {ticket.title}"
        if "description" in ticket_data:
            fields["description"] = ticket.description or ticket.title
        if "priority" in ticket_data or "severity" in ticket_data:
            priority_name = self._map_priority_to_jira(ticket.priority or ticket.severity)
            if priority_name:
                fields["priority"] = {"name": priority_name}
        if "assigned_to" in ticket_data:
            assignee_field = self._build_jira_assignee_field(
                self._resolve_external_assignee(ticket_data, config),
                config.assignee_identifier_type,
            )
            if assignee_field:
                fields["assignee"] = assignee_field
        return fields

    def _build_servicenow_update_payload(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if "title" in ticket_data:
            payload["short_description"] = f"[SentinelGrid] {ticket.title}"
        if "description" in ticket_data:
            payload["description"] = ticket.description or ticket.title
        if "status" in ticket_data:
            payload["state"] = self._map_status_to_servicenow_state(ticket.status)
        if "severity" in ticket_data or "priority" in ticket_data:
            sev = (ticket.severity or "medium").lower()
            mapped = self._map_severity_to_servicenow(sev)
            payload["severity"] = mapped
            payload["urgency"] = mapped
            payload["impact"] = mapped
        if ticket_data.get("assigned_to"):
            payload["assigned_to"] = ticket_data["assigned_to"]
        return payload

    async def _transition_jira_issue(
        self,
        external_ticket_id: str,
        status: str,
        config: TicketingHandoffConfig,
    ) -> Optional[str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._build_auth_headers(config.api_key),
        }
        base_url = config.url.rstrip("/")
        async with httpx.AsyncClient(timeout=15.0) as client:
            transitions_resp = await client.get(
                f"{base_url}/rest/api/2/issue/{external_ticket_id}/transitions",
                headers=headers,
            )
            transitions_resp.raise_for_status()
            transitions = (transitions_resp.json() or {}).get("transitions") or []
            transition_id = self._pick_jira_transition_id(transitions, status)
            if not transition_id:
                return None
            transition_resp = await client.post(
                f"{base_url}/rest/api/2/issue/{external_ticket_id}/transitions",
                headers=headers,
                json={"transition": {"id": transition_id}},
            )
            transition_resp.raise_for_status()
            return transition_id

    async def _update_jira_issue(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
    ) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._build_auth_headers(config.api_key),
        }
        base_url = config.url.rstrip("/")
        changed_fields = self._build_jira_update_fields(ticket, ticket_data, config)
        async with httpx.AsyncClient(timeout=15.0) as client:
            if changed_fields:
                update_resp = await client.put(
                    f"{base_url}/rest/api/2/issue/{ticket.external_vendor_id}",
                    headers=headers,
                    json={"fields": changed_fields},
                )
                update_resp.raise_for_status()

        transition_id = None
        if ticket_data.get("status"):
            transition_id = await self._transition_jira_issue(
                str(ticket.external_vendor_id),
                str(ticket.status),
                config,
            )
        return {
            "provider": "jira",
            "updated_fields": sorted(changed_fields.keys()),
            "transition_id": transition_id,
        }

    async def _resolve_servicenow_record_id(
        self,
        external_ticket_id: str,
        config: TicketingHandoffConfig,
    ) -> str:
        candidate = str(external_ticket_id)
        if re.fullmatch(r"[0-9a-fA-F]{32}", candidate):
            return candidate

        headers = {
            "Accept": "application/json",
            **self._build_auth_headers(config.api_key),
        }
        query_url = f"{config.url.rstrip('/')}/api/now/table/incident"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                query_url,
                headers=headers,
                params={
                    "sysparm_query": f"number={candidate}",
                    "sysparm_fields": "sys_id,number",
                    "sysparm_limit": 1,
                },
            )
            response.raise_for_status()
            results = (response.json() or {}).get("result") or []
            if not results:
                raise ValueError(f"ServiceNow incident {candidate} not found")
            return results[0].get("sys_id") or candidate

    async def _update_servicenow_incident(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
    ) -> Dict[str, Any]:
        record_id = await self._resolve_servicenow_record_id(
            str(ticket.external_vendor_id),
            config,
        )
        payload = self._build_servicenow_update_payload(ticket, ticket_data)
        if not payload:
            return {"provider": "servicenow", "updated_fields": []}

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._build_auth_headers(config.api_key),
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(
                f"{config.url.rstrip('/')}/api/now/table/incident/{record_id}",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        return {
            "provider": "servicenow",
            "updated_fields": sorted(payload.keys()),
            "record_id": record_id,
        }

    async def _add_jira_comment(
        self,
        ticket: Ticket,
        comment: str,
        config: TicketingHandoffConfig,
    ) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._build_auth_headers(config.api_key),
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{config.url.rstrip('/')}/rest/api/2/issue/{ticket.external_vendor_id}/comment",
                headers=headers,
                json={"body": comment},
            )
            response.raise_for_status()
            data = response.json()
        return {
            "provider": "jira",
            "comment_id": data.get("id"),
        }

    async def _add_servicenow_comment(
        self,
        ticket: Ticket,
        comment: str,
        config: TicketingHandoffConfig,
    ) -> Dict[str, Any]:
        record_id = await self._resolve_servicenow_record_id(
            str(ticket.external_vendor_id),
            config,
        )
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._build_auth_headers(config.api_key),
        }
        payload = {"comments": comment}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(
                f"{config.url.rstrip('/')}/api/now/table/incident/{record_id}",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        return {
            "provider": "servicenow",
            "record_id": record_id,
            "journal_field": "comments",
        }

    async def _sync_customer_managed_external_ticket_update(
        self,
        ticket: Ticket,
        ticket_data: Dict[str, Any],
        config: TicketingHandoffConfig,
    ) -> Dict[str, Any]:
        if config.provider == "jira":
            return await self._update_jira_issue(ticket, ticket_data, config)
        if config.provider == "servicenow":
            return await self._update_servicenow_incident(ticket, ticket_data, config)
        return {"provider": config.provider, "updated_fields": []}

    async def _sync_external_ticket_comment(
        self,
        ticket: Ticket,
        comment: str,
        config: TicketingHandoffConfig,
    ) -> Dict[str, Any]:
        if config.provider == "jira":
            return await self._add_jira_comment(ticket, comment, config)
        if config.provider == "servicenow":
            return await self._add_servicenow_comment(ticket, comment, config)
        return {"provider": config.provider}
    
    async def _map_to_frameworks_async(
        self,
        ticket: Ticket,
        tenant_id: Union[UUID, str]
    ):
        """Map ticket to NIST/MITRE frameworks asynchronously."""
        try:
            ticket_data = {
                "id": str(ticket.id),
                "tenant_id": str(tenant_id),
                "title": ticket.title,
                "description": ticket.description,
                "category": ticket.category,
                "severity": ticket.severity,
                "cve_ids": ticket.cve_ids or []
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json",
                    "X-Tenant-ID": str(tenant_id),
                }
                url = f"{self.framework_service_url}/api/v1/framework/map"
                payload = {
                    "ticket_data": ticket_data,
                    "tenant_id": str(tenant_id)
                }
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                mappings = response.json()
                
                # Update ticket with mappings
                from sqlalchemy.orm import Session
                # Note: Would need to get a new session here or pass db
                # For now, this is a placeholder
                logger.info(f"Mapped ticket {ticket.id} to frameworks: {mappings}")
        
        except Exception as e:
            logger.error(f"Error mapping ticket to frameworks: {e}")
    
    async def _trigger_enrichment_async(
        self,
        ticket_id: Union[UUID, str],
        tenant_id: Union[UUID, str]
    ):
        """Trigger AI enrichment asynchronously."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                url = f"{self.enrichment_agent_url}/api/v1/enrichment/ticket/{ticket_id}"
                params = {
                    "enrichment_type": "all",
                    "tenant_id": str(tenant_id)
                }
                response = await client.post(url, headers=headers, params=params)
                response.raise_for_status()
                logger.info(f"Enrichment triggered for ticket {ticket_id}")
        except Exception as e:
            logger.error(f"Error triggering enrichment for ticket {ticket_id}: {e}")

    async def _trigger_fixgroup_verification(
        self,
        tenant_id: Union[UUID, str],
        scan_id: Union[UUID, str] | str | None,
        fix_group_id: Union[UUID, str] | str | None,
    ) -> None:
        """Call orchestrator to kick off a verification scan for a FixGroup when a ticket is closed."""
        if not (scan_id and fix_group_id):
            return
        try:
            url = f"{self.scanner_orchestrator_url}/scans/{scan_id}/fix-groups/{fix_group_id}/verify"
            async with httpx.AsyncClient(timeout=10.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
                await client.post(url, params={"tenant_id": str(tenant_id)})
            logger.info("Triggered FixGroup verification scan=%s fg=%s tenant=%s", scan_id, fix_group_id, tenant_id)
        except Exception as exc:
            logger.warning("Failed to trigger FixGroup verification scan=%s fg=%s: %s", scan_id, fix_group_id, exc)

    async def _embed_ticket(self, tenant_id: Union[UUID, str], ticket: Ticket, assets: Optional[List[str]] = None):
        """Send ticket summary to embeddings for remediation chat."""
        try:
            if not self.model_gateway_url:
                return
            text_parts = [
                f"Title: {ticket.title}",
                f"Status: {ticket.status}",
            ]
            if ticket.description:
                text_parts.append(f"Description: {ticket.description}")
            if ticket.cve_ids:
                text_parts.append("CVEs: " + ", ".join(ticket.cve_ids))
            if assets:
                text_parts.append("Assets: " + ", ".join(assets))
            payload = {
                "summaries": [
                    {
                        "tenant_id": str(tenant_id),
                        "source": "ticket",
                        "agent_id": None,
                        "host_id": None,
                        "os_id": str(ticket.id),
                        "timestamp": datetime.utcnow().isoformat(),
                        "summary": " | ".join(text_parts),
                        "fields": {
                            "resource_type": "ticket",
                            "ticket_id": str(ticket.id),
                            "fix_group_id": (ticket.vm_data or {}).get("fix_group_id") if hasattr(ticket, "vm_data") else None,
                            "scan_id": (ticket.vm_data or {}).get("scan_id") if hasattr(ticket, "vm_data") else None,
                            "severity": ticket.severity,
                        },
                    }
                ]
            }
            async with httpx.AsyncClient(timeout=5.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
                await client.post(f"{self.model_gateway_url}/api/v1/embeddings/security-events", json=payload)
        except Exception as exc:
            logger.debug("Ticket embedding failed for ticket %s: %s", ticket.id, exc)
    
    async def _link_alerts(
        self,
        db: Session,
        ticket_id: Union[UUID, str],
        alert_ids: List[Union[UUID, str]],
        tenant_id: Union[UUID, str]
    ):
        """Link alerts to ticket."""
        try:
            from sg_core.models import ticket_alerts
        except Exception:
            logger.warning("ticket_alerts mapping not available; skipping alert linkage")
            return

        for alert_id in alert_ids:
            alert = db.query(Alert).filter(
                and_(Alert.id == alert_id, Alert.tenant_id == tenant_id)
            ).first()
            if alert:
                stmt = ticket_alerts.insert().values(ticket_id=ticket_id, alert_id=alert_id)
                db.execute(stmt)

        db.commit()
    
    async def _link_vulnerabilities(
        self,
        db: Session,
        ticket_id: Union[UUID, str],
        cve_ids: List[str],
        tenant_id: Union[UUID, str]
    ):
        """Link vulnerabilities to ticket."""
        try:
            from sg_core.models import Vulnerability, ticket_vulnerabilities  # type: ignore
        except Exception:
            logger.warning("Vulnerability model not available; skipping vulnerability linkage")
            return
        
        for cve_id in cve_ids:
            # Get or create vulnerability
            vulnerability = db.query(Vulnerability).filter(
                and_(
                    Vulnerability.cve_id == cve_id,
                    Vulnerability.tenant_id == tenant_id
                )
            ).first()
            
            if vulnerability:
                # Insert into ticket_vulnerabilities table
                stmt = ticket_vulnerabilities.insert().values(
                    ticket_id=ticket_id,
                    vulnerability_id=vulnerability.id
                )
                db.execute(stmt)
        
        db.commit()
    
    def _lookup_ticket(
        self,
        db: Session,
        ticket_id: Union[UUID, str],
        tenant_id: Union[UUID, str]
    ) -> Optional[Ticket]:
        """Get ticket by UUID or external_id/vendor_id for the tenant."""
        from sqlalchemy import or_
        uuid_val = None
        try:
            uuid_val = UUID(str(ticket_id))
        except Exception:
            uuid_val = None

        filters = [
            Ticket.tenant_id == tenant_id,
            or_(
                Ticket.id == uuid_val if uuid_val else False,  # False ignored by OR
                Ticket.external_id == str(ticket_id),
                Ticket.external_vendor_id == str(ticket_id),
            ),
        ]
        return db.query(Ticket).filter(and_(*filters)).first()

    def get_ticket(
        self,
        db: Session,
        ticket_id: Union[UUID, str],
        tenant_id: Union[UUID, str]
    ) -> Optional[Ticket]:
        """Get ticket by UUID or external id."""
        return self._lookup_ticket(db, ticket_id, tenant_id)
    
    async def update_ticket(
        self,
        db: Session,
        ticket_id: Union[UUID, str],
        tenant_id: Union[UUID, str],
        ticket_data: Dict[str, Any]
    ) -> Ticket:
        """Update ticket."""
        ticket = self._lookup_ticket(db, ticket_id, tenant_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        previous_status = ticket.status
        previous_assignee = getattr(ticket, "assigned_to", None)
        previous_due_date = getattr(ticket, "due_date", None)
        # Update fields
        for key, value in ticket_data.items():
            if hasattr(ticket, key) and key not in ["id", "tenant_id", "created_at"]:
                setattr(ticket, key, value)

        self._record_ticket_mutation_events(
            ticket,
            previous_status=previous_status,
            previous_assignee=previous_assignee,
            previous_due_date=previous_due_date,
            ticket_data=ticket_data,
        )
        ticket.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ticket)
        
        external_provider = (ticket.timeline_data or {}).get("external_ticket_provider")

        # Sync to Zammad if configured and external vendor id present
        if self.zammad and self.ticketing_provider == "zammad" and external_provider == "zammad" and ticket.external_vendor_id:
            await self.zammad.update_ticket(int(ticket.external_vendor_id), {
                "title": ticket.title,
                "state": ticket.status,
                "priority_id": self.zammad._map_priority(ticket.severity),
            })
        elif external_provider in {"jira", "servicenow"} and ticket.external_vendor_id:
            config = self.resolve_handoff_config(
                db,
                tenant_id,
                {"ticketing_provider": external_provider},
            )
            config.provider = external_provider
            config.customer_managed = True
            if config.url and config.api_key:
                try:
                    sync_result = await self._sync_customer_managed_external_ticket_update(
                        ticket,
                        ticket_data,
                        config,
                    )
                    ticket.timeline_data = self._append_timeline_event(
                        ticket.timeline_data,
                        "external_ticket_synced",
                        f"{external_provider.title()} handoff updated",
                        {
                            "provider": external_provider,
                            "external_id": ticket.external_vendor_id,
                            "updated_fields": sync_result.get("updated_fields", []),
                            "status": ticket.status,
                            "previous_status": previous_status,
                            "transition_id": sync_result.get("transition_id"),
                        },
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed syncing %s ticket update for ticket %s: %s",
                        external_provider,
                        ticket.id,
                        exc,
                    )
                    ticket.timeline_data = self._append_timeline_event(
                        ticket.timeline_data,
                        "external_ticket_sync_failed",
                        f"{external_provider.title()} handoff update failed",
                        {
                            "provider": external_provider,
                            "external_id": ticket.external_vendor_id,
                            "status": ticket.status,
                            "error": str(exc),
                        },
                    )
                db.commit()
                db.refresh(ticket)

        return ticket

    async def add_comment(
        self,
        db: Session,
        ticket_id: Union[UUID, str],
        tenant_id: Union[UUID, str],
        comment: str,
    ) -> Ticket:
        """Append a ticket comment and sync it to the downstream provider when supported."""
        ticket = self._lookup_ticket(db, ticket_id, tenant_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        comment_text = (comment or "").strip()
        if not comment_text:
            raise ValueError("Comment cannot be empty")

        ticket.timeline_data = self._append_comment_event(ticket.timeline_data, comment_text)
        ticket.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ticket)

        external_provider = (ticket.timeline_data or {}).get("external_ticket_provider")
        if external_provider in {"jira", "servicenow"} and ticket.external_vendor_id:
            config = self.resolve_handoff_config(
                db,
                tenant_id,
                {"ticketing_provider": external_provider},
            )
            config.provider = external_provider
            config.customer_managed = True
            if config.url and config.api_key:
                try:
                    sync_result = await self._sync_external_ticket_comment(ticket, comment_text, config)
                    ticket.timeline_data = self._append_timeline_event(
                        ticket.timeline_data,
                        "external_comment_synced",
                        f"{external_provider.title()} comment added",
                        {
                            "provider": external_provider,
                            "external_id": ticket.external_vendor_id,
                            "comment_id": sync_result.get("comment_id"),
                            "journal_field": sync_result.get("journal_field"),
                        },
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed syncing %s comment for ticket %s: %s",
                        external_provider,
                        ticket.id,
                        exc,
                    )
                    ticket.timeline_data = self._append_timeline_event(
                        ticket.timeline_data,
                        "external_comment_failed",
                        f"{external_provider.title()} comment sync failed",
                        {
                            "provider": external_provider,
                            "external_id": ticket.external_vendor_id,
                            "error": str(exc),
                        },
                    )
                db.commit()
                db.refresh(ticket)

        return ticket
    
    def search_tickets(
        self,
        db: Session,
        tenant_id: Union[UUID, str],
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Ticket]:
        """Search tickets."""
        query = db.query(Ticket).filter(Ticket.tenant_id == tenant_id)
        
        if status:
            query = query.filter(Ticket.status == status)
        if severity:
            query = query.filter(Ticket.severity == severity)
        if category:
            query = query.filter(Ticket.category == category)
        
        return query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()
