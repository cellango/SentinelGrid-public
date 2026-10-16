"""Rule engine for evaluating detection rules."""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.rule import DetectionRule
from app.rules import RULE_MAP
import asyncio

logger = logging.getLogger(__name__)


class RuleEngine:
    """Engine for evaluating detection rules against events."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def evaluate_rule(
        self,
        rule: DetectionRule,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate a single rule against events.
        
        Args:
            rule: DetectionRule database model
            events: Optional pre-fetched events. If None, will fetch based on rule configuration
        
        Returns:
            List of alerts generated
        """
        if not rule.enabled:
            logger.debug(f"Rule {rule.id} is disabled, skipping evaluation")
            return []
        
        # Get rule class
        rule_class = RULE_MAP.get(rule.rule_type)
        if not rule_class:
            logger.warning(f"Unknown rule type: {rule.rule_type}")
            return []
        
        try:
            # Create rule instance
            rule_instance = rule_class(
                rule_config={
                    "id": rule.id,
                    "name": rule.name,
                    "severity": rule.severity,
                    "pattern": rule.pattern,
                },
                tenant_id=str(rule.tenant_id),
            )
            
            # Fetch events if not provided
            if events is None:
                # Get lookback window from pattern (default 15 minutes)
                lookback_minutes = rule.pattern.get("lookback_minutes", 15)
                events = await rule_instance.fetch_recent_events(lookback_minutes=lookback_minutes)
            
            # Evaluate rule
            alerts = rule_instance.evaluate(events)
            
            logger.info(
                f"Rule {rule.name} ({rule.id}) evaluated: {len(events)} events, "
                f"{len(alerts)} alerts generated"
            )
            
            return alerts
        
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.id}: {e}", exc_info=True)
            return []
    
    async def evaluate_all_rules(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate all enabled rules for a tenant (or all tenants).
        
        Args:
            tenant_id: Optional tenant ID to filter
        
        Returns:
            Evaluation results
        """
        # Query enabled rules
        query = self.db.query(DetectionRule).filter(DetectionRule.enabled == True)
        
        if tenant_id:
            from uuid import UUID
            query = query.filter(DetectionRule.tenant_id == UUID(tenant_id))
        
        rules = query.all()
        
        results = {
            "total_rules": len(rules),
            "alerts_generated": 0,
            "rule_results": [],
        }
        
        for rule in rules:
            try:
                alerts = await self.evaluate_rule(rule)
                
                results["rule_results"].append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type,
                    "alerts_count": len(alerts),
                    "alerts": alerts,
                })
                
                results["alerts_generated"] += len(alerts)
            
            except Exception as e:
                logger.error(f"Failed to evaluate rule {rule.id}: {e}")
                results["rule_results"].append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type,
                    "alerts_count": 0,
                    "error": str(e),
                })
        
        return results

