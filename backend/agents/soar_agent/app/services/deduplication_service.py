"""
Detection event deduplication and suppression service.

Prevents alert fatigue by:
1. Deduplicating similar events (same user + same issue)
2. Suppressing repeated alerts within time windows
3. Escalating after threshold violations
"""

import hashlib
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DeduplicationService:
    """Service for deduplicating and suppressing detection events."""
    
    def __init__(self, db: Session):
        """
        Initialize deduplication service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def generate_dedup_key(
        self,
        alert_type: str,
        dedup_fields: Dict[str, Any]
    ) -> str:
        """
        Generate deduplication key from alert type and key fields.
        
        Args:
            alert_type: Alert type identifier
            dedup_fields: Fields to use for deduplication
        
        Returns:
            SHA-256 hash as dedup key
        """
        # Sort keys for consistent hashing
        sorted_fields = dict(sorted(dedup_fields.items()))
        
        # Create string representation
        dedup_str = f"{alert_type}:{json.dumps(sorted_fields, sort_keys=True)}"
        
        # Hash it
        return hashlib.sha256(dedup_str.encode()).hexdigest()
    
    def extract_dedup_fields(
        self,
        detection_event: Dict[str, Any],
        alert_type: str
    ) -> Dict[str, Any]:
        """
        Extract fields to use for deduplication based on alert type.
        
        Different alert types dedupe on different fields:
        - suspicious_login: user.id + source.ip
        - endpoint_malware: host.name + malware.hash
        - phishing_user_report: email.message_id
        etc.
        
        Args:
            detection_event: Detection event data
            alert_type: Alert type
        
        Returns:
            Dictionary of fields for deduplication
        """
        dedup_fields = {}
        
        if alert_type == "suspicious_login":
            # Dedupe by user + source IP
            if detection_event.get("user", {}).get("id"):
                dedup_fields["user_id"] = detection_event["user"]["id"]
            if detection_event.get("source", {}).get("ip"):
                dedup_fields["source_ip"] = detection_event["source"]["ip"]
        
        elif alert_type == "phishing_user_report":
            # Dedupe by email message ID
            if detection_event.get("email", {}).get("message_id"):
                dedup_fields["message_id"] = detection_event["email"]["message_id"]
        
        elif alert_type == "phishing_campaign":
            # Dedupe by campaign subject pattern
            if detection_event.get("campaign", {}).get("subject_pattern"):
                dedup_fields["subject_pattern"] = detection_event["campaign"]["subject_pattern"]
        
        elif alert_type in ["endpoint_malware", "ransomware_suspected"]:
            # Dedupe by host + malware hash
            if detection_event.get("host", {}).get("name"):
                dedup_fields["host_name"] = detection_event["host"]["name"]
            if detection_event.get("malware", {}).get("hash"):
                dedup_fields["malware_hash"] = detection_event["malware"]["hash"]
        
        elif alert_type == "cloud_storage_public":
            # Dedupe by cloud resource ID
            if detection_event.get("resource", {}).get("id"):
                dedup_fields["resource_id"] = detection_event["resource"]["id"]
            if detection_event.get("cloud", {}).get("account_id"):
                dedup_fields["account_id"] = detection_event["cloud"]["account_id"]
        
        elif alert_type == "privilege_escalation":
            # Dedupe by target user + role
            if detection_event.get("target_user", {}).get("id"):
                dedup_fields["target_user_id"] = detection_event["target_user"]["id"]
            if detection_event.get("iam", {}).get("role_name"):
                dedup_fields["role_name"] = detection_event["iam"]["role_name"]
        
        elif alert_type == "password_spray":
            # Dedupe by source IP (attacker)
            if detection_event.get("source", {}).get("ip"):
                dedup_fields["source_ip"] = detection_event["source"]["ip"]
        
        elif alert_type == "data_exfil_suspected":
            # Dedupe by user
            if detection_event.get("user", {}).get("id"):
                dedup_fields["user_id"] = detection_event["user"]["id"]
        
        elif alert_type == "lost_device":
            # Dedupe by device ID
            if detection_event.get("device", {}).get("id"):
                dedup_fields["device_id"] = detection_event["device"]["id"]
        
        return dedup_fields
    
    async def check_for_duplicate(
        self,
        detection_event: Dict[str, Any],
        tenant_id: str,
        time_window_minutes: int = 60
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if detection event is a duplicate.
        
        Args:
            detection_event: Detection event data
            tenant_id: Tenant UUID
            time_window_minutes: Time window for deduplication
        
        Returns:
            Tuple of (is_duplicate, dedup_record)
        """
        try:
            sg_context = detection_event.get("sg", {})
            rule_info = detection_event.get("rule", {})
            alert_type = sg_context.get("alert_type")
            
            # Extract fields for deduplication
            dedup_fields = self.extract_dedup_fields(detection_event, alert_type)
            
            if not dedup_fields:
                logger.debug(f"No dedup fields for alert_type={alert_type}, treating as unique")
                return False, None
            
            # Generate dedup key
            dedup_key = self.generate_dedup_key(alert_type, dedup_fields)
            
            # Check for existing dedup record
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
            
            query = text("""
                SELECT 
                    id, dedup_key, first_seen, last_seen, occurrence_count,
                    incident_id, status, suppressed_until
                FROM detection_deduplication
                WHERE tenant_id = :tenant_id
                  AND dedup_key = :dedup_key
                  AND status = 'active'
                  AND last_seen > :cutoff_time
                ORDER BY last_seen DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query, {
                "tenant_id": UUID(tenant_id),
                "dedup_key": dedup_key,
                "cutoff_time": cutoff_time
            }).fetchone()
            
            if result:
                # Found duplicate
                dedup_record = {
                    "id": result[0],
                    "dedup_key": result[1],
                    "first_seen": result[2],
                    "last_seen": result[3],
                    "occurrence_count": result[4],
                    "incident_id": result[5],
                    "status": result[6],
                    "suppressed_until": result[7]
                }
                
                logger.info(
                    f"Duplicate detected: dedup_key={dedup_key}, "
                    f"count={dedup_record['occurrence_count']}, "
                    f"first_seen={dedup_record['first_seen']}"
                )
                
                return True, dedup_record
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking for duplicate: {e}")
            # On error, treat as unique to avoid losing alerts
            return False, None
    
    async def update_dedup_record(
        self,
        dedup_id: UUID,
        detection_event_id: str
    ):
        """
        Update dedup record with new occurrence.
        
        Args:
            dedup_id: Deduplication record ID
            detection_event_id: New detection event ID
        """
        try:
            update_query = text("""
                UPDATE detection_deduplication
                SET last_seen = NOW(),
                    occurrence_count = occurrence_count + 1,
                    last_detection_event_id = :detection_event_id,
                    updated_at = NOW()
                WHERE id = :dedup_id
            """)
            
            self.db.execute(update_query, {
                "dedup_id": dedup_id,
                "detection_event_id": detection_event_id
            })
            self.db.commit()
            
            logger.info(f"Updated dedup record {dedup_id}")
            
        except Exception as e:
            logger.error(f"Error updating dedup record: {e}")
            self.db.rollback()
    
    async def create_dedup_record(
        self,
        detection_event: Dict[str, Any],
        tenant_id: str,
        rule_id: UUID,
        incident_id: Optional[UUID] = None
    ) -> UUID:
        """
        Create new dedup record.
        
        Args:
            detection_event: Detection event data
            tenant_id: Tenant UUID
            rule_id: Detection rule ID
            incident_id: Created incident ID (if any)
        
        Returns:
            Dedup record ID
        """
        try:
            alert_type = detection_event.get("sg", {}).get("alert_type")
            event_id = detection_event.get("event_id")

            if not rule_id:
                rule_key = detection_event.get("rule", {}).get("id")
                rule_id = self._resolve_rule_id(rule_key)
                if not rule_id:
                    logger.warning("Skipping dedup record because rule_id is missing (rule_key=%s)", rule_key)
                    return None
            
            # Extract dedup fields
            dedup_fields = self.extract_dedup_fields(detection_event, alert_type)
            dedup_key = self.generate_dedup_key(alert_type, dedup_fields)
            dedup_fields_json = json.dumps(dedup_fields)
            
            dedup_id = uuid4()
            
            insert_query = text("""
                INSERT INTO detection_deduplication (
                    id, tenant_id, rule_id, dedup_key, dedup_fields,
                    first_seen, last_seen, occurrence_count, incident_id,
                    last_detection_event_id, status, created_at, updated_at
                )
                VALUES (
                    :id, :tenant_id, :rule_id, :dedup_key, :dedup_fields,
                    NOW(), NOW(), 1, :incident_id, :detection_event_id,
                    'active', NOW(), NOW()
                )
            """)
            
            self.db.execute(insert_query, {
                "id": dedup_id,
                "tenant_id": UUID(tenant_id),
                "rule_id": rule_id,
                "dedup_key": dedup_key,
                "dedup_fields": dedup_fields_json,
                "incident_id": incident_id,
                "detection_event_id": event_id
            })
            self.db.commit()
            
            logger.info(f"Created dedup record {dedup_id} for {alert_type}")
            
            return dedup_id
            
        except Exception as e:
            logger.error(f"Error creating dedup record: {e}")
            self.db.rollback()
            raise

    def _resolve_rule_id(self, rule_key: Optional[str]) -> Optional[UUID]:
        """Best-effort lookup of detection_rules.id from a rule_key."""
        if not rule_key:
            return None
        try:
            row = self.db.execute(
                text(
                    "SELECT id FROM detection_rules "
                    "WHERE rule_key = :rule_key "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"rule_key": rule_key},
            ).mappings().first()
            if row and row.get("id"):
                return UUID(str(row["id"]))
        except Exception as exc:
            logger.warning("Rule lookup failed for rule_key=%s: %s", rule_key, exc)
        return None
    
    async def log_suppression_event(
        self,
        tenant_id: str,
        detection_event: Dict[str, Any],
        dedup_id: UUID,
        reason: str,
        suppression_rule_id: Optional[UUID] = None
    ):
        """
        Log a suppression event.
        
        Args:
            tenant_id: Tenant UUID
            detection_event: Detection event that was suppressed
            dedup_id: Deduplication record ID
            reason: Reason for suppression
            suppression_rule_id: Suppression rule that triggered (if any)
        """
        try:
            alert_type = detection_event.get("sg", {}).get("alert_type")
            event_id = detection_event.get("event_id")
            dedup_fields = self.extract_dedup_fields(detection_event, alert_type)
            dedup_key = self.generate_dedup_key(alert_type, dedup_fields)
            
            insert_query = text("""
                INSERT INTO detection_suppression_events (
                    id, tenant_id, dedup_id, suppression_rule_id,
                    detection_event_id, alert_type, suppressed_at,
                    reason, dedup_key, metadata
                )
                VALUES (
                    :id, :tenant_id, :dedup_id, :suppression_rule_id,
                    :detection_event_id, :alert_type, NOW(),
                    :reason, :dedup_key, :metadata
                )
            """)
            
            self.db.execute(insert_query, {
                "id": uuid4(),
                "tenant_id": UUID(tenant_id),
                "dedup_id": dedup_id,
                "suppression_rule_id": suppression_rule_id,
                "detection_event_id": event_id,
                "alert_type": alert_type,
                "reason": reason,
                "dedup_key": dedup_key,
                "metadata": detection_event.get("metadata", {})
            })
            self.db.commit()
            
            logger.info(
                f"Logged suppression: event={event_id}, reason={reason}, "
                f"dedup_key={dedup_key[:16]}..."
            )
            
        except Exception as e:
            logger.error(f"Error logging suppression event: {e}")
            self.db.rollback()
    
    async def should_suppress(
        self,
        detection_event: Dict[str, Any],
        tenant_id: str,
        dedup_record: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if detection event should be suppressed.
        
        Args:
            detection_event: Detection event data
            tenant_id: Tenant UUID
            dedup_record: Existing dedup record (if duplicate)
        
        Returns:
            Tuple of (should_suppress, reason)
        """
        try:
            sg_context = detection_event.get("sg", {})
            alert_type = sg_context.get("alert_type")
            severity = sg_context.get("severity")
            
            # If no dedup record, don't suppress
            if not dedup_record:
                return False, None
            
            # Check if currently suppressed with explicit suppression end time
            if dedup_record.get("suppressed_until"):
                if datetime.utcnow() < dedup_record["suppressed_until"]:
                    return True, "temporary_suppression"
            
            # Get suppression rules for this tenant and alert type
            rules = await self._get_suppression_rules(tenant_id, alert_type)
            
            for rule in rules:
                if not rule.get("enabled"):
                    continue
                
                # Check max occurrences
                max_occurrences = rule.get("max_occurrences", 1)
                current_count = dedup_record.get("occurrence_count", 0)
                
                if current_count >= max_occurrences:
                    # Check escalation policy
                    escalate_after = rule.get("escalate_after_count")
                    if escalate_after and current_count >= escalate_after:
                        # Escalate instead of suppress
                        logger.info(
                            f"Escalating: occurrence_count={current_count} >= "
                            f"escalate_after={escalate_after}"
                        )
                        return False, None  # Don't suppress, create incident
                    
                    # Check escalation by severity
                    escalate_severities = rule.get("escalate_if_severity", [])
                    if severity in escalate_severities:
                        logger.info(f"Escalating: severity={severity} in escalate_if_severity")
                        return False, None
                    
                    # Otherwise, suppress
                    return True, f"rate_limit_max_{max_occurrences}"
            
            # Default: don't suppress
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking suppression: {e}")
            # On error, don't suppress to avoid losing alerts
            return False, None
    
    async def _get_suppression_rules(
        self,
        tenant_id: str,
        alert_type: str
    ) -> List[Dict[str, Any]]:
        """Get suppression rules for tenant and alert type."""
        try:
            query = text("""
                SELECT 
                    id, name, alert_types, time_window_minutes,
                    max_occurrences, group_by_fields, escalate_after_count,
                    escalate_if_severity
                FROM detection_suppression_rules
                WHERE tenant_id = :tenant_id
                  AND enabled = true
                  AND (:alert_type = ANY(alert_types) OR alert_types IS NULL)
                ORDER BY created_at
            """)
            
            results = self.db.execute(query, {
                "tenant_id": UUID(tenant_id),
                "alert_type": alert_type
            }).fetchall()
            
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "alert_types": row[2],
                    "time_window_minutes": row[3],
                    "max_occurrences": row[4],
                    "group_by_fields": row[5],
                    "escalate_after_count": row[6],
                    "escalate_if_severity": row[7]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting suppression rules: {e}")
            return []
    
    async def process_detection_event(
        self,
        detection_event: Dict[str, Any],
        tenant_id: str,
        rule_id: UUID
    ) -> tuple[bool, Optional[UUID], Optional[str]]:
        """
        Process detection event through deduplication logic.
        
        Args:
            detection_event: Detection event data
            tenant_id: Tenant UUID
            rule_id: Detection rule ID
        
        Returns:
            Tuple of (create_incident, incident_id, suppression_reason)
            - create_incident: True if new incident should be created
            - incident_id: Existing incident ID if duplicate
            - suppression_reason: Reason if suppressed
        """
        try:
            event_id = detection_event.get("event_id")
            alert_type = detection_event.get("sg", {}).get("alert_type")
            
            # Check for duplicate
            is_duplicate, dedup_record = await self.check_for_duplicate(
                detection_event, tenant_id
            )
            
            if is_duplicate:
                # Update dedup record
                await self.update_dedup_record(
                    dedup_id=dedup_record["id"],
                    detection_event_id=event_id
                )
                
                # Check if should suppress
                should_suppress, reason = await self.should_suppress(
                    detection_event, tenant_id, dedup_record
                )
                
                if should_suppress:
                    # Log suppression
                    await self.log_suppression_event(
                        tenant_id=tenant_id,
                        detection_event=detection_event,
                        dedup_id=dedup_record["id"],
                        reason=reason
                    )
                    
                    logger.info(
                        f"Suppressed duplicate event {event_id}, "
                        f"reason={reason}, original_incident={dedup_record['incident_id']}"
                    )
                    
                    return False, dedup_record.get("incident_id"), reason
                else:
                    # Duplicate but should create incident (escalation)
                    logger.info(
                        f"Duplicate detected but creating incident (escalation), "
                        f"occurrence_count={dedup_record['occurrence_count'] + 1}"
                    )
                    return True, dedup_record.get("incident_id"), None
            else:
                # Not a duplicate, create incident
                logger.info(f"Unique detection event {event_id}, creating incident")
                return True, None, None
            
        except Exception as e:
            logger.error(f"Error processing detection event: {e}")
            # On error, create incident to avoid losing alerts
            return True, None, None


async def seed_default_suppression_rules(tenant_id: str, db: Session):
    """
    Seed default suppression rules for a tenant.
    
    These prevent alert fatigue while maintaining security visibility.
    """
    default_rules = [
        {
            "name": "Dedupe suspicious logins per user+IP (1 hour)",
            "description": "Only create 1 incident per user+IP combination per hour",
            "alert_types": ["suspicious_login"],
            "time_window_minutes": 60,
            "max_occurrences": 1,
            "group_by_fields": ["user.id", "source.ip"],
            "escalate_after_count": 5,  # Escalate after 5 attempts
            "escalate_if_severity": ["critical"]
        },
        {
            "name": "Dedupe malware per host+hash (4 hours)",
            "description": "Only create 1 incident per host+malware combination per 4 hours",
            "alert_types": ["endpoint_malware"],
            "time_window_minutes": 240,
            "max_occurrences": 1,
            "group_by_fields": ["host.name", "malware.hash"],
            "escalate_after_count": None,  # Always suppress duplicates
            "escalate_if_severity": ["critical"]
        },
        {
            "name": "Dedupe phishing reports by message ID",
            "description": "Only create 1 incident per unique email message",
            "alert_types": ["phishing_user_report"],
            "time_window_minutes": 1440,  # 24 hours
            "max_occurrences": 1,
            "group_by_fields": ["email.message_id"],
            "escalate_after_count": None
        },
        {
            "name": "Dedupe cloud misconfig per resource (24 hours)",
            "description": "Only create 1 incident per resource per day",
            "alert_types": ["cloud_storage_public"],
            "time_window_minutes": 1440,
            "max_occurrences": 1,
            "group_by_fields": ["resource.id", "cloud.account_id"],
            "escalate_after_count": 3  # Escalate if not fixed after 3 occurrences
        }
    ]
    
    insert_query = text("""
        INSERT INTO detection_suppression_rules (
            id, tenant_id, name, description, enabled, alert_types,
            time_window_minutes, max_occurrences, group_by_fields,
            escalate_after_count, escalate_if_severity, created_at, updated_at
        )
        VALUES (
            :id, :tenant_id, :name, :description, :enabled, :alert_types,
            :time_window_minutes, :max_occurrences, :group_by_fields,
            :escalate_after_count, :escalate_if_severity, NOW(), NOW()
        )
    """)
    
    for rule in default_rules:
        db.execute(insert_query, {
            "id": uuid4(),
            "tenant_id": UUID(tenant_id),
            "name": rule["name"],
            "description": rule["description"],
            "enabled": True,
            "alert_types": rule["alert_types"],
            "time_window_minutes": rule["time_window_minutes"],
            "max_occurrences": rule["max_occurrences"],
            "group_by_fields": rule["group_by_fields"],
            "escalate_after_count": rule.get("escalate_after_count"),
            "escalate_if_severity": rule.get("escalate_if_severity")
        })
    
    db.commit()
    logger.info(f"Seeded {len(default_rules)} default suppression rules for tenant {tenant_id}")


if __name__ == "__main__":
    import argparse
    import sys
    import os
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
    from app.core.database import get_db
    
    parser = argparse.ArgumentParser(description="Seed suppression rules")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    args = parser.parse_args()
    
    db = next(get_db())
    try:
        import asyncio
        asyncio.run(seed_default_suppression_rules(args.tenant_id, db))
        print(f"✓ Seeded suppression rules for tenant {args.tenant_id}")
    finally:
        db.close()
