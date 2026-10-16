"""Playbook trigger evaluation engine - evaluates alerts against playbook trigger conditions."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

# Import from sg_core for shared models
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.models import Alert, AlertPlaybookTrigger
from sqlalchemy import Table, MetaData

logger = logging.getLogger(__name__)


class PlaybookTriggerEngine:
    """Engine for evaluating alerts against playbook trigger conditions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def evaluate_alert(self, alert_id: UUID, tenant_id: UUID) -> List[Dict[str, Any]]:
        """
        Evaluate an alert against all enabled playbooks with auto-trigger enabled.
        
        Args:
            alert_id: Alert ID to evaluate
            tenant_id: Tenant ID
            
        Returns:
            List of matching playbooks with trigger reasons
        """
        # Get alert
        alert = self.db.query(Alert).filter(
            and_(Alert.id == alert_id, Alert.tenant_id == tenant_id)
        ).first()
        
        if not alert:
            logger.warning(f"Alert {alert_id} not found for tenant {tenant_id}")
            return []
        
        # Get all enabled playbooks with auto-trigger enabled for this tenant
        # Query playbooks table directly (it's in the main schema, not SOAR agent's schema)
        metadata = MetaData()
        playbooks_table = Table('playbooks', metadata, autoload_with=self.db.bind)
        
        stmt = select(playbooks_table).where(
            and_(
                playbooks_table.c.tenant_id == tenant_id,
                playbooks_table.c.is_enabled == True,
                playbooks_table.c.auto_trigger_enabled == True
            )
        ).order_by(playbooks_table.c.trigger_priority.desc())
        
        playbook_rows = self.db.execute(stmt).fetchall()
        
        matching_playbooks = []
        
        for playbook_row in playbook_rows:
            playbook_dict = dict(playbook_row._mapping)
            trigger_conditions = playbook_dict.get('trigger_conditions')
            
            if not trigger_conditions:
                continue
            
            # Evaluate trigger conditions
            if self._evaluate_conditions(alert, trigger_conditions):
                trigger_reason = self._generate_trigger_reason(alert, trigger_conditions)
                matching_playbooks.append({
                    "playbook_id": playbook_dict['id'],
                    "playbook_name": playbook_dict.get('name', 'Unknown'),
                    "trigger_reason": trigger_reason,
                    "priority": playbook_dict.get('trigger_priority', 0) or 0
                })
        
        # Sort by priority (higher first)
        matching_playbooks.sort(key=lambda x: x["priority"], reverse=True)
        
        logger.info(f"Found {len(matching_playbooks)} matching playbooks for alert {alert_id}")
        
        return matching_playbooks
    
    def _evaluate_conditions(self, alert: Alert, conditions: Dict[str, Any]) -> bool:
        """
        Evaluate alert against trigger conditions.
        
        Args:
            alert: Alert object
            conditions: Trigger conditions from playbook
            
        Returns:
            True if conditions match, False otherwise
        """
        # Severity condition
        if "severity" in conditions:
            severity_list = conditions["severity"]
            if isinstance(severity_list, str):
                severity_list = [severity_list]
            
            # Get alert severity (try AI analysis first, then raw_severity)
            alert_severity = None
            if hasattr(alert, 'ai_analyses') and alert.ai_analyses:
                # Get latest AI analysis
                alert_severity = alert.ai_analyses[-1].ai_severity if hasattr(alert.ai_analyses[-1], 'ai_severity') else None
            if not alert_severity:
                alert_severity = alert.raw_severity
            
            if alert_severity and alert_severity.lower() not in [s.lower() for s in severity_list]:
                return False
        
        # Category condition
        if "category" in conditions:
            category_list = conditions["category"]
            if isinstance(category_list, str):
                category_list = [category_list]
            
            # Get alert category (try AI analysis first)
            alert_category = None
            if hasattr(alert, 'ai_analyses') and alert.ai_analyses:
                alert_category = alert.ai_analyses[-1].ai_category if hasattr(alert.ai_analyses[-1], 'ai_category') else None
            
            if alert_category and alert_category.lower() not in [c.lower() for c in category_list]:
                return False
        
        # Source condition
        if "source" in conditions:
            source_list = conditions["source"]
            if isinstance(source_list, str):
                source_list = [source_list]
            
            if alert.source and alert.source.lower() not in [s.lower() for s in source_list]:
                return False
        
        # Time window condition (e.g., "5m", "1h")
        if "time_window" in conditions:
            time_window = conditions["time_window"]
            if not self._check_time_window(alert, time_window):
                return False
        
        # Threshold condition (e.g., minimum number of similar alerts)
        if "threshold" in conditions:
            threshold = conditions["threshold"]
            if not self._check_threshold(alert, threshold):
                return False
        
        # All conditions matched
        return True
    
    def _check_time_window(self, alert: Alert, time_window: str) -> bool:
        """
        Check if alert is within time window.
        
        Args:
            alert: Alert object
            time_window: Time window string (e.g., "5m", "1h", "24h")
            
        Returns:
            True if within window, False otherwise
        """
        try:
            # Parse time window
            if time_window.endswith("m"):
                minutes = int(time_window[:-1])
                delta = timedelta(minutes=minutes)
            elif time_window.endswith("h"):
                hours = int(time_window[:-1])
                delta = timedelta(hours=hours)
            elif time_window.endswith("d"):
                days = int(time_window[:-1])
                delta = timedelta(days=days)
            else:
                logger.warning(f"Invalid time window format: {time_window}")
                return True  # Don't filter if invalid
            
            # Check if alert is within time window
            now = datetime.utcnow()
            alert_time = alert.detection_time if hasattr(alert, 'detection_time') else alert.created_at
            
            if (now - alert_time) > delta:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking time window: {e}", exc_info=True)
            return True  # Don't filter on error
    
    def _check_threshold(self, alert: Alert, threshold: Dict[str, Any]) -> bool:
        """
        Check if alert meets threshold condition.
        
        Args:
            alert: Alert object
            threshold: Threshold configuration
            
        Returns:
            True if threshold met, False otherwise
        """
        # Example: Check for minimum number of similar alerts
        if "min_similar_alerts" in threshold:
            min_count = threshold["min_similar_alerts"]
            # Count similar alerts (same source, category, etc.)
            similar_count = self.db.query(Alert).filter(
                and_(
                    Alert.tenant_id == alert.tenant_id,
                    Alert.source == alert.source,
                    Alert.id != alert.id
                )
            ).count()
            
            if similar_count < min_count:
                return False
        
        return True
    
    def _generate_trigger_reason(self, alert: Alert, conditions: Dict[str, Any]) -> str:
        """
        Generate human-readable trigger reason.
        
        Args:
            alert: Alert object
            conditions: Trigger conditions
            
        Returns:
            Trigger reason string
        """
        reasons = []
        
        if "severity" in conditions:
            reasons.append(f"severity matches {conditions['severity']}")
        
        if "category" in conditions:
            reasons.append(f"category matches {conditions['category']}")
        
        if "source" in conditions:
            reasons.append(f"source matches {conditions['source']}")
        
        if "time_window" in conditions:
            reasons.append(f"within {conditions['time_window']} time window")
        
        return "; ".join(reasons) if reasons else "conditions matched"

