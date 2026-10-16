"""Incident creator service - creates incidents from detection events."""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import text

from sg_agent_runtime.soc_models import SOCCaseContext, SOCIncidentTriggerEvent

from app.services.nist_workflow import NISTWorkflowEngine, NISTStatus, NISTPhase
from app.services.deduplication_service import DeduplicationService
from app.services.soc_case_agent_bridge import SOCCaseAgentBridge

logger = logging.getLogger(__name__)


class IncidentCreator:
    """Service for creating incidents from detection events."""
    
    def __init__(
        self,
        db: Session,
        soc_case_agent_bridge: Optional[SOCCaseAgentBridge] = None,
    ):
        """
        Initialize incident creator.
        
        Args:
            db: Database session
        """
        self.db = db
        self.dedup_service = DeduplicationService(db)
        self.soc_case_agent_bridge = soc_case_agent_bridge or SOCCaseAgentBridge()
    
    async def create_incident_from_detection(
        self,
        detection_event: Dict[str, Any],
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Create an incident from a detection event.
        
        This method:
        1. Extracts relevant information from detection event
        2. Creates incident record in database
        3. Links to detection event
        4. Determines appropriate playbook
        5. Optionally auto-executes playbook
        
        Args:
            detection_event: Detection event data from OpenSearch
            tenant_id: Tenant UUID
        
        Returns:
            Dict with incident_id, playbook_execution_id, etc.
        """
        try:
            # Extract detection event fields
            sg_context = detection_event.get("sg", {})
            rule_info = detection_event.get("rule", {})
            event_id = detection_event.get("event_id")
            
            alert_type = sg_context.get("alert_type")
            severity = sg_context.get("severity", "medium")
            category = sg_context.get("category", "unknown")
            playbook_id_hint = sg_context.get("playbook_id")
            
            # Check for deduplication/suppression
            # This prevents alert fatigue from repeated identical detections
            create_incident, existing_incident_id, suppression_reason = await self.dedup_service.process_detection_event(
                detection_event=detection_event,
                tenant_id=tenant_id,
                rule_id=None  # Will be looked up from rule_info if needed
            )
            
            if not create_incident:
                logger.info(
                    f"Detection event {event_id} suppressed: {suppression_reason}, "
                    f"existing_incident={existing_incident_id}"
                )
                return {
                    "incident_id": str(existing_incident_id) if existing_incident_id else None,
                    "suppressed": True,
                    "suppression_reason": suppression_reason,
                    "message": "Detection event suppressed due to deduplication"
                }
            
            # Generate incident title from rule and entities
            title = self._generate_incident_title(detection_event, rule_info)
            
            # Generate description
            description = self._generate_incident_description(detection_event, rule_info)
            
            # Create incident in database with NIST workflow
            incident_id = uuid4()
            external_id = f"SG-INC-{incident_id.hex[:8].upper()}"
            
            # Get initial NIST status and phase
            nist_status = NISTWorkflowEngine.get_initial_status()
            nist_phase = NISTWorkflowEngine.get_initial_phase()
            
            # Insert incident with NIST status
            insert_incident = text("""
                INSERT INTO incidents (
                    id, tenant_id, source, external_id, title, status, severity, raw_payload,
                    created_at, updated_at
                )
                VALUES (
                    :id, :tenant_id, :source, :external_id, :title, :status, :severity, :raw_payload,
                    NOW(), NOW()
                )
                RETURNING id
            """)
            
            serialized_event = json.dumps(detection_event)

            result = self.db.execute(insert_incident, {
                "id": incident_id,
                "tenant_id": UUID(tenant_id),
                "source": "opensearch_detection",
                "external_id": external_id,
                "title": title,
                "status": nist_status.value,  # NIST status: NEW
                "severity": severity,
                "raw_payload": serialized_event
            })
            
            self.db.commit()
            
            logger.info(
                f"Created incident {incident_id} from detection event, "
                f"alert_type={alert_type}, NIST status={nist_status.value}, "
                f"phase={nist_phase.value}"
            )
            
            # Create deduplication record for this incident
            await self.dedup_service.create_dedup_record(
                detection_event=detection_event,
                tenant_id=tenant_id,
                rule_id=None,  # Will be looked up if needed
                incident_id=incident_id
            )
            
            # Create traceability records
            await self._create_traceability_records(
                incident_id=incident_id,
                detection_event=detection_event,
                tenant_id=tenant_id
            )
            
            # Extract observables from detection event
            await self._extract_observables(
                incident_id=incident_id,
                detection_event=detection_event,
                tenant_id=tenant_id
            )
            
            # Determine and execute playbook (if configured)
            playbook_execution_id = await self._handle_playbook_execution(
                incident_id=incident_id,
                tenant_id=tenant_id,
                alert_type=alert_type,
                playbook_id_hint=playbook_id_hint
            )

            soc_case_task_id = await self._trigger_soc_case_agent(
                incident_id=incident_id,
                external_id=external_id,
                tenant_id=tenant_id,
                detection_event=detection_event,
                title=title,
                severity=severity,
                status=nist_status.value,
                phase=nist_phase.value,
                playbook_execution_id=playbook_execution_id,
            )
            
            return {
                "incident_id": str(incident_id),
                "external_id": external_id,
                "title": title,
                "severity": severity,
                "status": "new",
                "playbook_execution_id": playbook_execution_id,
                "soc_case_task_id": soc_case_task_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating incident from detection event: {e}", exc_info=True)
            raise
    
    def _generate_incident_title(
        self,
        detection_event: Dict[str, Any],
        rule_info: Dict[str, Any]
    ) -> str:
        """Generate incident title from detection event."""
        rule_name = rule_info.get("name", "Unknown Detection")
        sg_context = detection_event.get("sg", {})
        
        # Try to add entity information to title
        user = detection_event.get("user", {})
        host = detection_event.get("host", {})
        source = detection_event.get("source", {})
        
        if user.get("email"):
            return f"{rule_name} - User: {user['email']}"
        elif host.get("name"):
            return f"{rule_name} - Host: {host['name']}"
        elif source.get("ip"):
            return f"{rule_name} - IP: {source['ip']}"
        else:
            return rule_name
    
    def _generate_incident_description(
        self,
        detection_event: Dict[str, Any],
        rule_info: Dict[str, Any]
    ) -> str:
        """Generate incident description from detection event."""
        lines = []
        
        # Rule information
        lines.append(f"Detection Rule: {rule_info.get('name', 'Unknown')}")
        lines.append(f"Rule ID: {rule_info.get('id', 'Unknown')}")
        lines.append(f"Rule Version: {rule_info.get('version', '1.0.0')}")
        lines.append("")
        
        # Detection details
        if detection_event.get("description"):
            lines.append(f"Description: {detection_event['description']}")
            lines.append("")
        
        # Entity details
        user = detection_event.get("user", {})
        if user:
            lines.append("User Information:")
            if user.get("email"):
                lines.append(f"  - Email: {user['email']}")
            if user.get("id"):
                lines.append(f"  - ID: {user['id']}")
            lines.append("")
        
        host = detection_event.get("host", {})
        if host:
            lines.append("Host Information:")
            if host.get("name"):
                lines.append(f"  - Name: {host['name']}")
            if host.get("ip"):
                lines.append(f"  - IP: {host['ip']}")
            lines.append("")
        
        source = detection_event.get("source", {})
        if source:
            lines.append("Source Information:")
            if source.get("ip"):
                lines.append(f"  - IP: {source['ip']}")
            if source.get("geo"):
                lines.append(f"  - Location: {source['geo'].get('country', 'Unknown')}")
            lines.append("")
        
        return "\n".join(lines)
    
    async def _create_traceability_records(
        self,
        incident_id: UUID,
        detection_event: Dict[str, Any],
        tenant_id: str
    ):
        """Create traceability records for incident lifecycle tracking."""
        try:
            event_id = detection_event.get("event_id")
            rule_info = detection_event.get("rule", {})
            sg_context = detection_event.get("sg", {})
            
            # Create incident lifecycle record linking to detection event
            insert_lifecycle = text("""
                INSERT INTO incident_lifecycle (
                    id, incident_id, detection_event_id, alert_raw_payload, created_at
                )
                VALUES (
                    :id, :incident_id, :detection_event_id, :alert_raw_payload, NOW()
                )
            """)
            
            self.db.execute(insert_lifecycle, {
                "id": uuid4(),
                "incident_id": incident_id,
                "detection_event_id": event_id,
                "alert_raw_payload": json.dumps(detection_event)
            })
            
            # Create initial timeline entry
            nist_status = NISTWorkflowEngine.get_initial_status()
            nist_phase = NISTWorkflowEngine.get_initial_phase()
            
            insert_timeline = text("""
                INSERT INTO incident_timeline (
                    id, incident_id, timestamp, event_type, actor_type, actor_id,
                    nist_phase, nist_status, action, description, metadata, success
                )
                VALUES (
                    :id, :incident_id, NOW(), :event_type, :actor_type, :actor_id,
                    :nist_phase, :nist_status, :action, :description, :metadata, :success
                )
            """)
            
            self.db.execute(insert_timeline, {
                "id": uuid4(),
                "incident_id": incident_id,
                "event_type": "detection",
                "actor_type": "system",
                "actor_id": "opensearch_monitor",
                "nist_phase": nist_phase.value,
                "nist_status": nist_status.value,
                "action": "detected",
                "description": f"Incident created from detection rule {rule_info.get('id', 'unknown')}",
                "metadata": json.dumps({
                    "detection_event_id": event_id,
                    "rule_key": rule_info.get("id"),
                    "alert_type": sg_context.get("alert_type"),
                    "severity": sg_context.get("severity")
                }),
                "success": True
            })
            
            self.db.commit()
            
            logger.info(
                f"Traceability: Created lifecycle and timeline records for incident {incident_id}, "
                f"detection_event_id={event_id}"
            )
            
        except Exception as e:
            logger.error(f"Error creating traceability records: {e}")
            # Don't fail incident creation if traceability fails
            # But log the error for investigation
    
    async def _extract_observables(
        self,
        incident_id: UUID,
        detection_event: Dict[str, Any],
        tenant_id: str
    ):
        """Extract observables (IOCs) from detection event."""
        try:
            observables = []
            
            # Extract IP addresses
            if detection_event.get("source", {}).get("ip"):
                observables.append({
                    "type": "ip",
                    "value": detection_event["source"]["ip"],
                    "source": "detection_rule"
                })
            
            # Extract email addresses
            if detection_event.get("user", {}).get("email"):
                observables.append({
                    "type": "email",
                    "value": detection_event["user"]["email"],
                    "source": "detection_rule"
                })
            
            # Extract file hashes
            if detection_event.get("malware", {}).get("hash"):
                observables.append({
                    "type": "file_hash",
                    "value": detection_event["malware"]["hash"],
                    "source": "detection_rule"
                })
            
            # Extract domains
            if detection_event.get("email", {}).get("from"):
                from_addr = detection_event["email"]["from"]
                if "@" in from_addr:
                    domain = from_addr.split("@")[1]
                    observables.append({
                        "type": "domain",
                        "value": domain,
                        "source": "detection_rule"
                    })
            
            # Extract hostnames
            if detection_event.get("host", {}).get("name"):
                observables.append({
                    "type": "host",
                    "value": detection_event["host"]["name"],
                    "source": "detection_rule"
                })
            
            # Insert observables into database
            if observables:
                insert_observable = text("""
                    INSERT INTO incident_observables (
                        id, incident_id, observable_type, observable_value, source,
                        extracted_at, extracted_by, confidence, first_seen, last_seen
                    )
                    VALUES (
                        :id, :incident_id, :observable_type, :observable_value, :source,
                        NOW(), :extracted_by, :confidence, NOW(), NOW()
                    )
                """)
                
                for obs in observables:
                    self.db.execute(insert_observable, {
                        "id": uuid4(),
                        "incident_id": incident_id,
                        "observable_type": obs["type"],
                        "observable_value": obs["value"],
                        "source": obs["source"],
                        "extracted_by": "system_detection",
                        "confidence": 0.8  # Default confidence for detection-extracted IOCs
                    })
                
                self.db.commit()
                
                logger.info(
                    f"Extracted and stored {len(observables)} observables for incident {incident_id}"
                )
            
        except Exception as e:
            logger.error(f"Error extracting observables: {e}")
            # Don't fail incident creation if observable extraction fails
    
    async def _handle_playbook_execution(
        self,
        incident_id: UUID,
        tenant_id: str,
        alert_type: str,
        playbook_id_hint: Optional[str] = None
    ) -> Optional[str]:
        """
        Determine appropriate playbook and execute if configured.
        
        Args:
            incident_id: Incident UUID
            tenant_id: Tenant UUID
            alert_type: Alert type from detection event
            playbook_id_hint: Optional playbook ID from detection event
        
        Returns:
            Playbook execution ID if executed, None otherwise
        """
        try:
            from app.services.playbook_mapping_loader import PlaybookMappingLoader
            
            # Look up playbook mapping for this alert type
            mapping_loader = PlaybookMappingLoader(self.db)
            mapping = mapping_loader.get_mapping_for_alert_type(tenant_id, alert_type)
            
            if not mapping:
                logger.warning(
                    f"No playbook mapping found for alert_type={alert_type}, "
                    f"tenant={tenant_id}"
                )
                return None
            
            logger.info(
                f"Playbook mapping found: {alert_type} → {mapping['playbook_key']}, "
                f"auto_execute={mapping['auto_execute']}"
            )
            
            # Check if auto-execute is enabled
            if not mapping.get("auto_execute", False):
                logger.info(
                    f"Auto-execute disabled for {alert_type}, "
                    "playbook will not be executed automatically"
                )
                return None
            
            # Log playbook execution intent (actual execution logic to be implemented)
            logger.info(
                f"Would execute playbook {mapping['playbook_key']} "
                f"for incident {incident_id}"
            )
            
            # TODO: Implement actual playbook execution
            # 1. Look up playbook by key
            # 2. Create playbook_executions record
            # 3. Trigger workflow engine
            # 4. Return execution ID
            
            return None  # Placeholder - will return execution_id when implemented
            
        except Exception as e:
            logger.error(f"Error handling playbook execution: {e}")
            # Don't fail incident creation if playbook execution fails
            return None

    async def _trigger_soc_case_agent(
        self,
        incident_id: UUID,
        external_id: str,
        tenant_id: str,
        detection_event: Dict[str, Any],
        title: str,
        severity: str,
        status: str,
        phase: str,
        playbook_execution_id: Optional[str] = None,
    ) -> Optional[str]:
        """Persist incident-scoped case state and submit the SOC case-agent task."""
        try:
            case_context = self._build_soc_case_context(
                incident_id=incident_id,
                external_id=external_id,
                tenant_id=tenant_id,
                detection_event=detection_event,
                title=title,
                severity=severity,
                status=status,
                phase=phase,
                playbook_execution_id=playbook_execution_id,
            )
            trigger_event = SOCIncidentTriggerEvent(
                trigger_type="incident_created",
                incident_id=str(incident_id),
                tenant_id=tenant_id,
                source_kind="detection_event",
                source_event_id=str(detection_event.get("event_id") or ""),
                changed_fields=["status", "severity", "raw_payload"],
                reason="Detection event created a new incident",
            )
            result = await self.soc_case_agent_bridge.initialize_case(case_context, trigger_event)
            return result.get("task_id")
        except Exception as exc:
            logger.error(
                "Failed to initialize SOC case-agent workflow for incident %s: %s",
                incident_id,
                exc,
                exc_info=True,
            )
            return None

    def _build_soc_case_context(
        self,
        incident_id: UUID,
        external_id: str,
        tenant_id: str,
        detection_event: Dict[str, Any],
        title: str,
        severity: str,
        status: str,
        phase: str,
        playbook_execution_id: Optional[str] = None,
    ) -> SOCCaseContext:
        """Build the canonical incident-scoped case context for the SOC AI Agent."""
        sg_context = detection_event.get("sg", {})
        rule_info = detection_event.get("rule", {})

        related_detection = {
            "id": str(detection_event.get("event_id") or incident_id),
            "source": "opensearch_detection",
            "label": rule_info.get("name") or title,
            "record_type": "detection_event",
            "metadata": {
                "severity": str(severity),
                "alert_type": str(sg_context.get("alert_type") or ""),
            },
        }

        observables = []
        source_ip = detection_event.get("source", {}).get("ip")
        user_email = detection_event.get("user", {}).get("email")
        host_name = detection_event.get("host", {}).get("name")
        if source_ip:
            observables.append(
                {
                    "id": source_ip,
                    "source": "detection_event",
                    "label": source_ip,
                    "record_type": "ip",
                }
            )
        if user_email:
            observables.append(
                {
                    "id": user_email,
                    "source": "detection_event",
                    "label": user_email,
                    "record_type": "email",
                }
            )
        if host_name:
            observables.append(
                {
                    "id": host_name,
                    "source": "detection_event",
                    "label": host_name,
                    "record_type": "host",
                }
            )

        entities = []
        if user_email:
            entities.append(
                {
                    "id": user_email,
                    "source": "identity",
                    "label": user_email,
                    "record_type": "user",
                }
            )
        if host_name:
            entities.append(
                {
                    "id": host_name,
                    "source": "endpoint",
                    "label": host_name,
                    "record_type": "host",
                }
            )

        executed_playbooks = []
        if playbook_execution_id:
            executed_playbooks.append(
                {
                    "id": playbook_execution_id,
                    "source": "soar_agent",
                    "label": "Initial automatic playbook execution",
                    "record_type": "playbook_execution",
                }
            )

        ticket_refs = [
            {
                "id": external_id,
                "source": "soar_agent",
                "label": external_id,
                "record_type": "incident_external_id",
            }
        ]

        open_questions = [
            "Confirm the affected identities, assets, and blast radius.",
            "Validate the best response pack and playbook for this case.",
            "Decide whether containment needs human approval immediately.",
        ]

        return SOCCaseContext(
            incident_id=str(incident_id),
            tenant_id=tenant_id,
            incident_title=title,
            incident_type=(
                sg_context.get("alert_type")
                or sg_context.get("category")
                or rule_info.get("name")
                or "security_incident"
            ),
            severity=severity,
            status=status,
            phase=phase,
            related_detections=[related_detection],
            related_observables=observables,
            entities=entities,
            mitre_tactics=self._extract_framework_tokens(detection_event, "mitre_tactics", "tactic_id"),
            mitre_techniques=self._extract_framework_tokens(detection_event, "mitre_techniques", "technique_id"),
            nist_controls=self._extract_framework_tokens(detection_event, "nist_controls", "control_id"),
            ticket_refs=ticket_refs,
            executed_playbooks=executed_playbooks,
            open_questions=open_questions,
        )

    @staticmethod
    def _extract_framework_tokens(
        detection_event: Dict[str, Any],
        field_name: str,
        dict_key: str,
    ) -> list[str]:
        """Extract normalized framework tokens from detection payloads."""
        collected = []
        for container in (
            detection_event,
            detection_event.get("sg", {}),
            detection_event.get("rule", {}),
        ):
            values = container.get(field_name) if isinstance(container, dict) else None
            if not values:
                continue
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if isinstance(value, dict):
                    token = value.get(dict_key) or value.get("id") or value.get("name")
                else:
                    token = value
                if token and str(token) not in collected:
                    collected.append(str(token))
        return collected
