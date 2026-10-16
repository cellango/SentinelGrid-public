"""New Admin User detection rule."""

import logging
from typing import List, Dict, Any
from datetime import datetime
from app.rules.base import BaseRule

logger = logging.getLogger(__name__)


class NewAdminRule(BaseRule):
    """Detect when a new admin user is created."""
    
    def evaluate(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate events for new admin user creation.
        
        Pattern: User with admin role created
        """
        alerts = []
        
        # Extract configuration
        admin_keywords = self.pattern.get("admin_keywords", ["admin", "administrator", "root"])
        check_groups = self.pattern.get("check_groups", True)
        
        for event in events:
            # Check for user creation events
            event_type = event.get("event_type", "").lower()
            event_name = event.get("event_name", "").lower()
            action = event.get("action", "").lower()
            
            is_user_creation = (
                "createuser" in event_type or
                "createuser" in event_name or
                "user.create" in event_type or
                "user_created" in event_type or
                action in ["create", "create_user", "user.create"]
            )
            
            if not is_user_creation:
                continue
            
            # Check if user has admin privileges
            user = event.get("user", {})
            user_name = user.get("name", "").lower()
            user_email = user.get("email", "").lower()
            user_id = user.get("id", "")
            
            # Check username for admin keywords
            is_admin = any(keyword in user_name for keyword in admin_keywords)
            
            # Check roles/groups
            if not is_admin and check_groups:
                roles = event.get("roles", [])
                groups = event.get("groups", [])
                
                for role in roles:
                    role_name = str(role).lower() if isinstance(role, (str, dict)) else ""
                    if isinstance(role, dict):
                        role_name = role.get("name", "").lower()
                    
                    if any(keyword in role_name for keyword in admin_keywords):
                        is_admin = True
                        break
                
                for group in groups:
                    group_name = str(group).lower() if isinstance(group, (str, dict)) else ""
                    if isinstance(group, dict):
                        group_name = group.get("name", "").lower()
                    
                    if any(keyword in group_name for keyword in admin_keywords):
                        is_admin = True
                        break
            
            # Check IAM policies for AWS events
            if not is_admin:
                request_params = event.get("request_parameters", {})
                if request_params:
                    # Check for admin policy attachments
                    policy_arn = request_params.get("policyArn", "")
                    if "AdministratorAccess" in policy_arn or "PowerUserAccess" in policy_arn:
                        is_admin = True
            
            if is_admin:
                # Create alert
                alert = self.create_alert(
                    title=f"New Admin User Created - {user_name or user_email or user_id}",
                    description=(
                        f"A new user with administrator privileges was created: "
                        f"{user_name or user_email or user_id}"
                    ),
                    events=[event],
                    metadata={
                        "user_id": user_id,
                        "user_name": user_name,
                        "user_email": user_email,
                        "created_at": event.get("@timestamp") or event.get("timestamp"),
                    },
                )
                alerts.append(alert)
        
        return alerts
    
    def get_rule_type(self) -> str:
        return "new_admin"

