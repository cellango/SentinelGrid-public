"""Incident metadata service for storing enhancement data."""

import logging
from typing import Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from uuid import UUID

from sg_core.models import Incident, Ticket
from app.services.thehive_service import TheHiveService

logger = logging.getLogger(__name__)


class IncidentMetadataService:
    """Service for managing incident metadata (NIST/MITRE, AI enrichment)."""
    
    def __init__(self):
        self.thehive_service = TheHiveService()
    
    def create_incident_metadata(
        self,
        db: Session,
        ticket_id: Union[UUID, str],
        tenant_id: Union[UUID, str],
        thehive_case_id: Optional[str] = None,
        nist_controls: Optional[Dict[str, Any]] = None,
        mitre_tactics: Optional[Dict[str, Any]] = None,
        mitre_techniques: Optional[Dict[str, Any]] = None,
        ai_summary: Optional[str] = None,
    ) -> Incident:
        """
        Create incident metadata from a ticket.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            tenant_id: Tenant ID
            thehive_case_id: TheHive case ID (if already created)
            nist_controls: NIST control mappings
            mitre_tactics: MITRE tactic mappings
            mitre_techniques: MITRE technique mappings
            ai_summary: AI-generated summary
        
        Returns:
            Created Incident object
        """
        # Get ticket
        ticket = db.query(Ticket).filter(
            and_(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()
        
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Create or update incident metadata
        incident = db.query(Incident).filter(
            and_(
                Incident.external_id == thehive_case_id or ticket.external_id,
                Incident.tenant_id == tenant_id
            )
        ).first()
        
        if incident:
            # Update existing
            incident.title = ticket.title
            incident.status = ticket.status
            incident.severity = ticket.severity
            if nist_controls:
                incident.nist_controls = nist_controls
            if mitre_tactics:
                incident.mitre_tactics = mitre_tactics
            if mitre_techniques:
                incident.mitre_techniques = mitre_techniques
            incident.updated_at = datetime.utcnow()
        else:
            # Create new
            incident = Incident(
                tenant_id=tenant_id,
                source="thehive",
                external_id=thehive_case_id or ticket.external_id or f"ticket-{ticket_id}",
                title=ticket.title,
                status=ticket.status,
                severity=ticket.severity,
                nist_controls=nist_controls or ticket.nist_controls,
                mitre_tactics=mitre_tactics or ticket.mitre_tactics,
                mitre_techniques=mitre_techniques or ticket.mitre_techniques,
                raw_payload={
                    "ticket_id": str(ticket_id),
                    "ai_summary": ai_summary,
                } if ai_summary else None
            )
            db.add(incident)
        
        db.commit()
        db.refresh(incident)
        
        return incident
    
    async def sync_with_thehive(
        self,
        db: Session,
        incident_id: Union[UUID, str],
        tenant_id: Union[UUID, str]
    ) -> Incident:
        """
        Sync incident metadata with TheHive case.
        
        Args:
            db: Database session
            incident_id: Incident ID
            tenant_id: Tenant ID
        
        Returns:
            Updated Incident object
        """
        incident = db.query(Incident).filter(
            and_(
                Incident.id == incident_id,
                Incident.tenant_id == tenant_id
            )
        ).first()
        
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        
        if not incident.external_id:
            logger.warning(f"Incident {incident_id} has no external_id, cannot sync")
            return incident
        
        try:
            # Fetch case from TheHive
            case = await self.thehive_service.get_case(incident.external_id)
            
            # Update incident with TheHive data
            thehive_status = case.get("status", "").lower()
            status_map = {
                "open": "open",
                "inprogress": "in_progress",
                "resolved": "resolved",
                "closed": "closed",
            }
            incident.status = status_map.get(thehive_status, incident.status)
            
            thehive_severity = case.get("severity")
            if thehive_severity:
                severity_map = {4: "critical", 3: "high", 2: "medium", 1: "low"}
                incident.severity = severity_map.get(thehive_severity, incident.severity)
            
            # Cache TheHive case data
            incident.raw_payload = case
            
            incident.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(incident)
            
            logger.info(f"Synced incident {incident_id} with TheHive case {incident.external_id}")
        
        except Exception as e:
            logger.error(f"Error syncing incident with TheHive: {e}")
        
        return incident
    
    def get_incident_metadata(
        self,
        db: Session,
        incident_id: Union[UUID, str],
        tenant_id: Union[UUID, str]
    ) -> Optional[Incident]:
        """Get incident metadata."""
        return db.query(Incident).filter(
            and_(
                Incident.id == incident_id,
                Incident.tenant_id == tenant_id
            )
        ).first()
    
    def get_incident_by_thehive_case(
        self,
        db: Session,
        thehive_case_id: str,
        tenant_id: Union[UUID, str]
    ) -> Optional[Incident]:
        """Get incident by TheHive case ID."""
        return db.query(Incident).filter(
            and_(
                Incident.external_id == thehive_case_id,
                Incident.tenant_id == tenant_id
            )
        ).first()

