"""Main enrichment service orchestrator."""

import logging
import asyncio
from typing import Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID

from sg_core.models import TicketAIEnrichment, Ticket
from app.services.iam_enrichment import IAMEnrichmentModule
from app.services.vulnerability_enrichment import VulnerabilityEnrichmentModule
from app.services.cmdb_enrichment import CMDBEnrichmentModule
from app.services.network_enrichment import NetworkEnrichmentModule
from app.services.framework_mapping import FrameworkMappingModule
from app.core.config import settings

logger = logging.getLogger(__name__)


class EnrichmentStatus:
    """Enrichment status constants."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EnrichmentService:
    """Orchestrates AI enrichment for tickets."""
    
    def __init__(self):
        self.iam_module = IAMEnrichmentModule()
        self.vuln_module = VulnerabilityEnrichmentModule()
        self.cmdb_module = CMDBEnrichmentModule()
        self.network_module = NetworkEnrichmentModule()
        self.framework_module = FrameworkMappingModule()
    
    async def enrich_ticket(
        self,
        db: Session,
        ticket_id: Union[UUID, str],
        tenant_id: Union[UUID, str],
        enrichment_type: str = "all"
    ) -> TicketAIEnrichment:
        """
        Enrich a ticket with AI-generated data.
        
        Args:
            db: Database session
            ticket_id: Ticket ID
            tenant_id: Tenant ID
            enrichment_type: Type of enrichment (iam, vulnerability, cmdb, network, all)
        
        Returns:
            TicketAIEnrichment object
        """
        # Get ticket data
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.tenant_id == tenant_id
        ).first()
        
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Create enrichment record
        enrichment = TicketAIEnrichment(
            ticket_id=ticket_id,
            tenant_id=tenant_id,
            enrichment_type=enrichment_type,
        )
        db.add(enrichment)
        db.commit()
        db.refresh(enrichment)
        
        try:
            # Convert ticket to dictionary for enrichment
            ticket_data = {
                "id": str(ticket.id),
                "tenant_id": str(ticket.tenant_id),
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status,
                "severity": ticket.severity,
                "category": ticket.category,
                "user_identifier": None,  # Extract from alerts if needed
                "asset_id": None,  # Extract from alerts if needed
                "cve_ids": ticket.cve_ids or [],
                "exploit_indicators": ticket.exploit_indicators or {},
                "nist_controls": ticket.nist_controls or [],
                "mitre_tactics": ticket.mitre_tactics or [],
                "mitre_techniques": ticket.mitre_techniques or [],
                "alerts": []  # Would fetch linked alerts
            }
            
            # Parallel enrichment across modules
            enrichment_tasks = []
            
            if enrichment_type in ["all", "iam"]:
                enrichment_tasks.append(
                    ("iam", self.iam_module.enrich(ticket_data))
                )
            
            if enrichment_type in ["all", "vulnerability"]:
                enrichment_tasks.append(
                    ("vulnerability", self.vuln_module.enrich(ticket_data))
                )
            
            if enrichment_type in ["all", "cmdb"]:
                enrichment_tasks.append(
                    ("cmdb", self.cmdb_module.enrich(ticket_data))
                )
            
            if enrichment_type in ["all", "network"]:
                enrichment_tasks.append(
                    ("network", self.network_module.enrich(ticket_data))
                )
            
            if enrichment_type in ["all", "framework"]:
                enrichment_tasks.append(
                    ("framework", self.framework_module.enrich(ticket_data))
                )
            
            # Execute enrichment in parallel if enabled
            if settings.PARALLEL_ENRICHMENT and len(enrichment_tasks) > 1:
                results = await asyncio.gather(
                    *[task[1] for task in enrichment_tasks],
                    return_exceptions=True
                )
            else:
                # Sequential execution
                results = []
                for task in enrichment_tasks:
                    try:
                        result = await task[1]
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error in {task[0]} enrichment: {e}")
                        results.append(e)
            
            # Process results
            for i, (task_name, result) in enumerate(zip([t[0] for t in enrichment_tasks], results)):
                if isinstance(result, Exception):
                    logger.error(f"Enrichment {task_name} failed: {result}")
                    continue
                
                if task_name == "iam":
                    enrichment.iam_enrichment = result
                elif task_name == "vulnerability":
                    enrichment.vulnerability_enrichment = result
                elif task_name == "cmdb":
                    enrichment.cmdb_enrichment = result
                elif task_name == "network":
                    enrichment.network_enrichment = result
                elif task_name == "framework":
                    enrichment.framework_enrichment = result
            
            # Update ticket with enrichment data
            await self._update_ticket_with_enrichment(db, ticket, enrichment)
            
            # Generate AI summary (would integrate with Model Gateway)
            enrichment.ai_enrichment_summary = await self._generate_summary(enrichment)
            
            enrichment.status = EnrichmentStatus.COMPLETED
            enrichment.completed_at = datetime.utcnow()
            enrichment.model_name = "sentinelgrid-enrichment"
            enrichment.model_version = "1.0"
        
        except Exception as e:
            logger.error(f"Error enriching ticket {ticket_id}: {e}")
            enrichment.status = EnrichmentStatus.FAILED
            enrichment.reasoning = str(e)
            enrichment.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(enrichment)
        
        return enrichment
    
    async def _update_ticket_with_enrichment(
        self,
        db: Session,
        ticket: Ticket,
        enrichment: TicketAIEnrichment
    ):
        """Update ticket with enrichment data."""
        # Update ticket tab data
        if enrichment.iam_enrichment:
            ticket.iam_data = enrichment.iam_enrichment
        
        if enrichment.vulnerability_enrichment:
            ticket.vm_data = enrichment.vulnerability_enrichment
        
        if enrichment.cmdb_enrichment:
            ticket.cmdb_data = enrichment.cmdb_enrichment
        
        if enrichment.network_enrichment:
            ticket.network_data = enrichment.network_enrichment
        
        # Update framework mappings
        if enrichment.framework_enrichment:
            framework_data = enrichment.framework_enrichment
            if framework_data.get("nist_controls"):
                ticket.nist_controls = framework_data["nist_controls"]
            if framework_data.get("mitre_tactics"):
                ticket.mitre_tactics = framework_data["mitre_tactics"]
            if framework_data.get("mitre_techniques"):
                ticket.mitre_techniques = framework_data["mitre_techniques"]
        
        # Update enrichment status
        ticket.ai_enrichment_status = enrichment.status
        ticket.ai_enrichment_summary = enrichment.ai_enrichment_summary
        ticket.ai_enrichment_timestamp = enrichment.completed_at
        
        db.commit()
    
    async def _generate_summary(self, enrichment: TicketAIEnrichment) -> str:
        """Generate AI summary of enrichment (placeholder - would use Model Gateway)."""
        # Placeholder - would integrate with Model Gateway for AI summarization
        summary_parts = []
        
        if enrichment.iam_enrichment and enrichment.iam_enrichment.get("users"):
            summary_parts.append(f"Found {len(enrichment.iam_enrichment['users'])} user(s) associated with this ticket.")
        
        if enrichment.vulnerability_enrichment and enrichment.vulnerability_enrichment.get("vulnerabilities"):
            summary_parts.append(f"Identified {len(enrichment.vulnerability_enrichment['vulnerabilities'])} vulnerability/vulnerabilities.")
        
        if enrichment.cmdb_enrichment and enrichment.cmdb_enrichment.get("assets"):
            summary_parts.append(f"Found {len(enrichment.cmdb_enrichment['assets'])} asset(s) associated with this ticket.")
        
        return " ".join(summary_parts) if summary_parts else "Enrichment completed."
    
    def get_enrichment(
        self,
        db: Session,
        ticket_id: Union[UUID, str],
        tenant_id: Union[UUID, str]
    ) -> Optional[TicketAIEnrichment]:
        """Get enrichment for a ticket."""
        return db.query(TicketAIEnrichment).filter(
            TicketAIEnrichment.ticket_id == ticket_id,
            TicketAIEnrichment.tenant_id == tenant_id
        ).order_by(TicketAIEnrichment.created_at.desc()).first()
