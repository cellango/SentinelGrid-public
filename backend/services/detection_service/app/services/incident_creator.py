"""Incident creation service for high-severity alerts."""

import logging
import asyncio
import sys
import os
from typing import Dict, Any, Optional, Union
from datetime import datetime
from uuid import UUID, uuid4
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure sg_core is importable inside the service container
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../libs")))

from sg_core.models import Tenant, Incident
from sg_core.entity_model import build_story_context
from sg_events.workflow import (
    WorkflowEventType,
    WorkflowStage,
    publish_workflow_event,
)
from sg_agent_runtime.soc_case_runtime_client import SOCCaseRuntimeClient
from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine)


class IncidentCreator:
    """Service for creating incidents/tickets from alerts."""
    
    def __init__(self):
        self.ticketing_service_url = settings.TICKETING_SERVICE_URL if hasattr(settings, 'TICKETING_SERVICE_URL') else "http://ticketing_service:8000"
        self.framework_service_url = settings.FRAMEWORK_SERVICE_URL if hasattr(settings, 'FRAMEWORK_SERVICE_URL') else "http://framework_service:8000"
        self.agent_runtime_url = settings.AGENT_RUNTIME_URL if hasattr(settings, "AGENT_RUNTIME_URL") else "http://agent_runtime:8000"
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
        self.default_realm = os.getenv("REALM_NAME", "demo")
    
    async def create_incident_from_alert(
        self,
        alert_data: Dict[str, Any],
        ai_analysis: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[Union[UUID, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create an incident/ticket from an alert.
        
        Args:
            alert_data: Alert data dictionary
            ai_analysis: AI analysis results (optional)
            tenant_id: Tenant ID
        
        Returns:
            Created ticket data or None
        """
        # Determine if incident should be created
        severity = ai_analysis.get("ai_severity") if ai_analysis else alert_data.get("raw_severity", "low")

        # Fetch tenant incident mode from DB if not provided
        incident_mode = alert_data.get("incident_management_mode")
        if not incident_mode and tenant_id:
            try:
                with SessionLocal() as session:
                    tenant_row = session.query(Tenant).filter(Tenant.id == tenant_id).first()
                    if tenant_row and tenant_row.incident_management_mode:
                        incident_mode = tenant_row.incident_management_mode
            except Exception as e:
                logger.warning(f"Failed to fetch tenant incident mode: {e}")
        incident_mode = incident_mode or "saas_managed"
        
        # Only create incidents for high/critical severity
        if severity not in ["high", "critical"]:
            logger.debug(f"Alert {alert_data.get('id')} severity {severity} below threshold, skipping incident creation")
            return None
        if incident_mode == "customer_managed":
            logger.info(
                "Tenant %s is customer-managed; creating the SentinelGrid incident and delegating downstream handoff to the customer-managed ticketing workflow for alert %s",
                tenant_id,
                alert_data.get("id"),
            )
        
        try:
            # Prepare incident + ticket data
            dedup_key = f"{tenant_id}:{alert_data.get('source')}:{alert_data.get('asset_id') or alert_data.get('user_identifier')}"
            incident_id = uuid4()
            incident_external_id = f"SG-INC-{str(incident_id)[:8]}"

            incident_raw = {
                **(alert_data.get("raw_payload") or {}),
                "dedup_key": dedup_key,
                "incident_management_mode": incident_mode,
                "suppression_reason": alert_data.get("suppression_reason"),
                "audit": [
                    {
                        "ts": datetime.utcnow().isoformat(),
                        "text": "Incident created from alert",
                        "actor": "system",
                    }
                ],
            }
            related_alert_ids = list(incident_raw.get("related_alert_ids") or [])
            origin_alert_id = alert_data.get("id")
            if origin_alert_id:
                related_alert_ids.append(str(origin_alert_id))
            if related_alert_ids:
                incident_raw["related_alert_ids"] = list(dict.fromkeys(str(alert_id) for alert_id in related_alert_ids))
            if alert_data.get("asset_id"):
                incident_raw["asset_id"] = alert_data.get("asset_id")
            if alert_data.get("user_identifier"):
                incident_raw["user_identifier"] = alert_data.get("user_identifier")
            if alert_data.get("detection_rule_id"):
                incident_raw["detection_rule_id"] = alert_data.get("detection_rule_id")
            if alert_data.get("detection_rule_version_id"):
                incident_raw["detection_rule_version_id"] = alert_data.get("detection_rule_version_id")
            if alert_data.get("playbook_version_id"):
                incident_raw["playbook_version_id"] = alert_data.get("playbook_version_id")
            incident_raw.update(
                build_story_context(
                    raw_payload=incident_raw,
                    asset_id=alert_data.get("asset_id"),
                    user_identifier=alert_data.get("user_identifier"),
                    detection_rule_id=alert_data.get("detection_rule_id"),
                    detection_rule_version_id=alert_data.get("detection_rule_version_id"),
                    playbook_id=alert_data.get("recommended_playbook"),
                    playbook_version_id=alert_data.get("playbook_version_id"),
                    related_detections=[
                        {
                            "id": str(origin_alert_id),
                            "title": alert_data.get("title"),
                            "severity": severity,
                        }
                    ]
                    if origin_alert_id
                    else None,
                    cve_ids=alert_data.get("cve_ids"),
                )
            )

            # Create incident record
            with SessionLocal() as session:
                inc = Incident(
                    id=incident_id,
                    tenant_id=tenant_id,
                    source="detection_service",
                    external_id=incident_external_id,
                    title=alert_data.get("title", "Security Alert"),
                    status="open",
                    severity=severity,
                    raw_payload=incident_raw,
                    nist_controls=alert_data.get("nist_controls"),
                    mitre_tactics=alert_data.get("mitre_tactics"),
                    mitre_techniques=alert_data.get("mitre_techniques"),
                    cve_ids=alert_data.get("cve_ids"),
                    exploit_indicators=alert_data.get("exploit_indicators"),
                )
                session.add(inc)
                session.commit()
                try:
                    publish_workflow_event(
                        event_type=WorkflowEventType.ALERT_PROMOTED_TO_INCIDENT,
                        stage=WorkflowStage.INCIDENT,
                        tenant_id=tenant_id,
                        workflow_id=incident_id,
                        source_service="detection_service",
                        title="Alert promoted to incident",
                        resource_type="incident",
                        resource_id=incident_id,
                        resource_name=inc.title,
                        related_resources=[
                            {
                                "type": "alert",
                                "id": str(origin_alert_id) if origin_alert_id else None,
                                "title": alert_data.get("title"),
                            }
                        ]
                        if origin_alert_id
                        else [],
                        metadata={
                            "dedup_key": dedup_key,
                            "severity": severity,
                            "incident_management_mode": incident_mode,
                        },
                        db_session=session,
                        realm_name=self.default_realm,
                    )
                    if origin_alert_id:
                        publish_workflow_event(
                            event_type=WorkflowEventType.ALERT_PROMOTED_TO_INCIDENT,
                            stage=WorkflowStage.INCIDENT,
                            tenant_id=tenant_id,
                            workflow_id=incident_id,
                            source_service="detection_service",
                            title="Incident created from this alert",
                            resource_type="alert",
                            resource_id=origin_alert_id,
                            resource_name=alert_data.get("title"),
                            related_resources=[
                                {
                                    "type": "incident",
                                    "id": str(incident_id),
                                    "title": inc.title,
                                }
                            ],
                            metadata={
                                "incident_id": str(incident_id),
                                "dedup_key": dedup_key,
                                "severity": severity,
                            },
                            db_session=session,
                            realm_name=self.default_realm,
                        )
                except Exception as workflow_err:
                    logger.warning(
                        "Failed to record workflow event for incident %s: %s",
                        incident_id,
                        workflow_err,
                    )

            soc_case_task: Optional[Dict[str, Any]] = None
            try:
                soc_case_task = await self._submit_soc_case_triage_task(
                    tenant_id=tenant_id,
                    incident_id=incident_id,
                    alert_data=alert_data,
                    ai_analysis=ai_analysis,
                    severity=severity,
                    incident_raw=incident_raw,
                )
            except Exception as soc_case_err:
                logger.warning(
                    "Failed submitting SOC case-agent triage task for incident %s: %s",
                    incident_id,
                    soc_case_err,
                )

            ticket_data = {
                "title": alert_data.get("title", "Security Alert"),
                "description": alert_data.get("description") or ai_analysis.get("rationale") if ai_analysis else None,
                "status": "open",
                "severity": severity,
                "priority": self._map_severity_to_priority(severity),
                "category": ai_analysis.get("ai_category") if ai_analysis else "security_alert",
                "source": "detection_service",
                "alert_ids": [str(alert_data.get("id"))],
                "cve_ids": alert_data.get("cve_ids", []),
                "exploit_indicators": alert_data.get("exploit_indicators", {}),
                "created_by": "system",
                "dedup_key": dedup_key,
                "suppression_reason": alert_data.get("suppression_reason"),
                "asset_id": alert_data.get("asset_id"),
                "user_identifier": alert_data.get("user_identifier"),
                "recommended_playbook": alert_data.get("recommended_playbook"),
                "nist_controls": alert_data.get("nist_controls"),
                "mitre_tactics": alert_data.get("mitre_tactics"),
                "mitre_techniques": alert_data.get("mitre_techniques"),
                "incident_id": str(incident_id),
            }
            
            # Map to frameworks (async)
            framework_mappings = await self._map_to_frameworks(alert_data, ai_analysis)
            if framework_mappings:
                ticket_data["nist_controls"] = framework_mappings.get("nist_controls", [])
                ticket_data["mitre_tactics"] = framework_mappings.get("mitre_tactics", [])
                ticket_data["mitre_techniques"] = framework_mappings.get("mitre_techniques", [])

            # Add incident mode into payload for downstream services
            ticket_data["incident_management_mode"] = incident_mode
            ticket_data["workflow_id"] = str(incident_id)

            try:
                with SessionLocal() as session:
                    publish_workflow_event(
                        event_type=WorkflowEventType.INCIDENT_TICKET_REQUESTED,
                        stage=WorkflowStage.TICKETING,
                        tenant_id=tenant_id,
                        workflow_id=incident_id,
                        source_service="detection_service",
                        title="Ticket creation requested for incident",
                        resource_type="incident",
                        resource_id=incident_id,
                        resource_name=alert_data.get("title", "Security Alert"),
                        related_resources=[
                            {
                                "type": "alert",
                                "id": str(origin_alert_id) if origin_alert_id else None,
                                "title": alert_data.get("title"),
                            }
                        ]
                        if origin_alert_id
                        else [],
                        metadata={
                            "severity": severity,
                            "incident_management_mode": incident_mode,
                            "ticket_category": ticket_data.get("category"),
                        },
                        db_session=session,
                        realm_name=self.default_realm,
                    )
            except Exception as workflow_err:
                logger.warning(
                    "Failed to record ticket request workflow event for incident %s: %s",
                    incident_id,
                    workflow_err,
                )

            # Create ticket via Ticketing Service
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json"
                }
                url = f"{self.ticketing_service_url}/api/v1/tickets"
                params = {"tenant_id": str(tenant_id)} if tenant_id else {}
                response = await client.post(url, headers=headers, json=ticket_data, params=params)
                response.raise_for_status()
                
                ticket = response.json()
                if soc_case_task and soc_case_task.get("id"):
                    ticket["soc_case_task_id"] = soc_case_task["id"]
                logger.info(f"Created ticket {ticket.get('id')} from alert {alert_data.get('id')}")

                # Update incident with ticket refs
                try:
                    with SessionLocal() as session:
                        inc = session.query(Incident).filter(Incident.id == incident_id, Incident.tenant_id == tenant_id).first()
                        if inc:
                            inc.ticket_id = UUID(ticket.get("id")) if ticket.get("id") else None
                            inc.external_ticket_id = ticket.get("external_id")
                            inc.external_ticket_provider = ticket.get("source") or ticket.get("external_ticket_provider")
                            # append audit entry
                            rp = inc.raw_payload or {}
                            audit = rp.get("audit", [])
                            if isinstance(audit, list):
                                audit.append({
                                    "ts": datetime.utcnow().isoformat(),
                                    "text": f"Ticket created: {inc.external_ticket_id or inc.ticket_id}",
                                    "actor": "system"
                                })
                            rp["audit"] = audit
                            inc.raw_payload = rp
                            session.commit()
                            try:
                                publish_workflow_event(
                                    event_type=WorkflowEventType.TICKET_CREATED,
                                    stage=WorkflowStage.TICKETING,
                                    tenant_id=tenant_id,
                                    workflow_id=incident_id,
                                    source_service="detection_service",
                                    title="Incident linked to created ticket",
                                    resource_type="incident",
                                    resource_id=incident_id,
                                    resource_name=inc.title,
                                    related_resources=[
                                        {
                                            "type": "ticket",
                                            "id": ticket.get("id"),
                                            "title": ticket.get("title") or inc.title,
                                        }
                                    ],
                                    metadata={
                                        "ticket_id": ticket.get("id"),
                                        "external_ticket_id": inc.external_ticket_id,
                                        "provider": inc.external_ticket_provider,
                                        "dedup_key": dedup_key,
                                    },
                                    db_session=session,
                                    realm_name=self.default_realm,
                                )
                            except Exception as workflow_err:
                                logger.warning(
                                    "Failed to record created ticket workflow event for ticket %s: %s",
                                    ticket.get("id"),
                                    workflow_err,
                                )
                except Exception as e:
                    logger.warning(f"Failed to update incident {incident_id} with ticket refs: {e}")

                return ticket
        
        except Exception as e:
            logger.error(f"Error creating incident from alert: {e}")
            try:
                if tenant_id:
                    with SessionLocal() as session:
                        publish_workflow_event(
                            event_type=WorkflowEventType.WORKFLOW_FAILED,
                            stage=WorkflowStage.TICKETING,
                            tenant_id=tenant_id,
                            workflow_id=incident_id if 'incident_id' in locals() else origin_alert_id or uuid4(),
                            source_service="detection_service",
                            title="Alert handoff workflow failed",
                            resource_type="incident" if 'incident_id' in locals() else "alert",
                            resource_id=incident_id if 'incident_id' in locals() else (origin_alert_id or uuid4()),
                            resource_name=alert_data.get("title"),
                            related_resources=[
                                {
                                    "type": "alert",
                                    "id": str(origin_alert_id) if origin_alert_id else None,
                                    "title": alert_data.get("title"),
                                }
                            ]
                            if origin_alert_id
                            else [],
                            metadata={
                                "severity": severity,
                                "error": str(e),
                            },
                            success=False,
                            error_message=str(e),
                            db_session=session,
                            realm_name=self.default_realm,
                        )
            except Exception as workflow_err:
                logger.warning("Failed to record workflow failure event: %s", workflow_err)
            return None

    async def _submit_soc_case_triage_task(
        self,
        *,
        tenant_id: Optional[Union[UUID, str]],
        incident_id: UUID,
        alert_data: Dict[str, Any],
        ai_analysis: Optional[Dict[str, Any]],
        severity: str,
        incident_raw: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Submit the initial deterministic SOC case-agent task for a new incident."""
        if not tenant_id:
            logger.warning(
                "SOC case-agent triage task skipped for incident %s because tenant_id is missing",
                incident_id,
            )
            return None

        alert_id = alert_data.get("id")
        category = (
            ai_analysis.get("ai_category")
            if ai_analysis
            else alert_data.get("category") or alert_data.get("alert_type") or "security_alert"
        )
        priority = str(severity or "medium").lower()
        if priority not in {"low", "medium", "high", "critical"}:
            priority = "medium"

        client = SOCCaseRuntimeClient(
            runtime_url=self.agent_runtime_url,
            internal_token=self.internal_token,
        )
        return await client.submit_case_refresh(
            tenant_id=str(tenant_id),
            incident_id=str(incident_id),
            trigger_type="incident_created",
            source_kind="detection_alert",
            source_event_id=str(alert_id) if alert_id else None,
            priority=priority,
            reason="High-severity detection was promoted to a SentinelGrid incident.",
            payload={
                "incident_title": alert_data.get("title") or "Security Alert",
                "incident_type": category,
                "category": category,
                "severity": severity,
                "status": "open",
                "phase": incident_raw.get("phase") or "detection_and_analysis",
                "source": "detection_service",
                "alert_id": str(alert_id) if alert_id else None,
                "asset_id": alert_data.get("asset_id"),
                "user_identifier": alert_data.get("user_identifier"),
                "detection_rule_id": alert_data.get("detection_rule_id"),
                "detection_rule_version_id": alert_data.get("detection_rule_version_id"),
                "playbook_version_id": alert_data.get("playbook_version_id"),
                "recommended_playbook": alert_data.get("recommended_playbook"),
                "nist_controls": alert_data.get("nist_controls") or [],
                "mitre_tactics": alert_data.get("mitre_tactics") or [],
                "mitre_techniques": alert_data.get("mitre_techniques") or [],
                "cve_ids": alert_data.get("cve_ids") or [],
                "related_alert_ids": incident_raw.get("related_alert_ids") or [],
            },
        )
    
    async def _map_to_frameworks(
        self,
        alert_data: Dict[str, Any],
        ai_analysis: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Map alert to NIST/MITRE frameworks."""
        try:
            incident_data = {
                "title": alert_data.get("title"),
                "description": alert_data.get("description"),
                "category": ai_analysis.get("ai_category") if ai_analysis else "security_alert",
                "severity": ai_analysis.get("ai_severity") if ai_analysis else alert_data.get("raw_severity"),
                "cve_ids": alert_data.get("cve_ids", [])
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                tenant_id = alert_data.get("tenant_id")
                headers = {
                    "Authorization": f"Bearer {self.internal_token}",
                    "Content-Type": "application/json",
                }
                if tenant_id:
                    headers["X-Tenant-ID"] = str(tenant_id)
                url = f"{self.framework_service_url}/api/v1/framework/map"
                payload = {
                    "ticket_data": incident_data,
                    "tenant_id": tenant_id
                }
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Could not map to frameworks: {e}")
            return None
    
    def _map_severity_to_priority(self, severity: str) -> str:
        """Map severity to priority."""
        mapping = {
            "critical": "P1",
            "high": "P2",
            "medium": "P3",
            "low": "P4"
        }
        return mapping.get(severity.lower(), "P3")
