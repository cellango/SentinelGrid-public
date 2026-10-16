"""Multiple Failed Logins detection rule."""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
from app.rules.base import BaseRule

logger = logging.getLogger(__name__)


class FailedLoginsRule(BaseRule):
    """Detect multiple failed login attempts within a time window."""
    
    def evaluate(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate events for multiple failed logins.
        
        Pattern: 5+ failed logins within 15 minutes (default)
        """
        alerts = []
        
        # Extract configuration
        threshold = self.pattern.get("threshold", 5)
        window_minutes = self.pattern.get("window_minutes", 15)
        
        # Group events by user/email
        user_events = defaultdict(list)
        
        for event in events:
            # Filter for login failure events
            event_type = event.get("event_type", "")
            if "login.failure" not in event_type.lower() and "login_failure" not in event_type.lower():
                continue
            
            # Extract user identifier
            user = event.get("user", {})
            user_id = user.get("email") or user.get("id") or user.get("name")
            
            if not user_id:
                continue
            
            # Extract timestamp
            timestamp_str = event.get("@timestamp") or event.get("timestamp")
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except:
                    timestamp = datetime.utcnow()
            elif isinstance(timestamp_str, datetime):
                timestamp = timestamp_str
            else:
                timestamp = datetime.utcnow()
            
            user_events[user_id].append({
                **event,
                "_timestamp": timestamp,
            })
        
        # Check each user for threshold violations
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        for user_id, user_event_list in user_events.items():
            # Filter events within the time window
            recent_failures = [
                e for e in user_event_list
                if e["_timestamp"] >= window_start
            ]
            
            if len(recent_failures) >= threshold:
                # Create alert
                alert = self.create_alert(
                    title=f"Multiple Failed Login Attempts - {user_id}",
                    description=(
                        f"User {user_id} has {len(recent_failures)} failed login attempts "
                        f"within the last {window_minutes} minutes (threshold: {threshold})"
                    ),
                    events=recent_failures,
                    metadata={
                        "user_id": user_id,
                        "failure_count": len(recent_failures),
                        "threshold": threshold,
                        "window_minutes": window_minutes,
                        "first_failure": min(e["_timestamp"] for e in recent_failures).isoformat(),
                        "last_failure": max(e["_timestamp"] for e in recent_failures).isoformat(),
                    },
                )
                alerts.append(alert)
        
        return alerts
    
    def get_rule_type(self) -> str:
        return "failed_logins"

