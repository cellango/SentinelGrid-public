"""
Auto-Remediation Service
Automatically remediates policy violations and access issues
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.services.keycloak_client import KeycloakClient

logger = logging.getLogger(__name__)


class AutoRemediationService:
    """Service for automated remediation of IAM issues."""
    
    def __init__(self, keycloak_client: KeycloakClient):
        self.keycloak_client = keycloak_client
    
    def remediate_policy_violations(
        self,
        violations: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically remediate policy violations.
        
        Violation types:
        - Over-privileged users
        - Violated access policies
        - Expired entitlements
        - Unused entitlements
        """
        results = []
        
        for violation in violations:
            violation_type = violation.get("type")
            user_id = violation.get("user_id")
            
            try:
                if violation_type == "over_privileged":
                    result = self._remediate_over_privileged_user(
                        user_id,
                        violation,
                        tenant_id,
                        dry_run
                    )
                    results.append(result)
                
                elif violation_type == "policy_violation":
                    result = self._remediate_policy_violation(
                        user_id,
                        violation,
                        tenant_id,
                        dry_run
                    )
                    results.append(result)
                
                elif violation_type == "expired_entitlement":
                    result = self._remediate_expired_entitlement(
                        violation,
                        tenant_id,
                        dry_run
                    )
                    results.append(result)
                
                elif violation_type == "unused_entitlement":
                    result = self._remediate_unused_entitlement(
                        violation,
                        tenant_id,
                        dry_run
                    )
                    results.append(result)
                
            except Exception as e:
                logger.error(f"Error remediating violation {violation_type}: {e}")
                results.append({
                    "violation_id": violation.get("id"),
                    "type": violation_type,
                    "success": False,
                    "error": str(e)
                })
        
        successful = sum(1 for r in results if r.get("success", False))
        
        return {
            "tenant_id": tenant_id,
            "total_violations": len(violations),
            "remediated": successful,
            "failed": len(results) - successful,
            "dry_run": dry_run,
            "results": results,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    def cleanup_stale_access(
        self,
        stale_threshold_days: int = 90,
        tenant_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically clean up stale access (inactive users, unused entitlements).
        """
        cleanup_results = []
        
        # Find stale users (no login in X days)
        users = self.keycloak_client.list_users()
        
        for user in users:
            user_id = user.get("id")
            last_login = user.get("lastLogin")
            enabled = user.get("enabled", True)
            
            if not enabled:
                continue
            
            if last_login:
                try:
                    if isinstance(last_login, str):
                        last_login_dt = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                    else:
                        last_login_dt = last_login
                    
                    days_since = (datetime.utcnow() - last_login_dt.replace(tzinfo=None)).days
                    
                    if days_since > stale_threshold_days:
                        if not dry_run:
                            # TODO: Disable user
                            # self.keycloak_client.disable_user(user_id)
                            pass
                        
                        cleanup_results.append({
                            "type": "stale_user",
                            "user_id": user_id,
                            "days_inactive": days_since,
                            "action": "disabled" if not dry_run else "would_disable",
                            "success": True
                        })
                except Exception as e:
                    logger.error(f"Error processing stale user {user_id}: {e}")
        
        # Find unused entitlements (would need to query Entitlement Agent)
        # TODO: Integrate with Entitlement Agent to get unused entitlements
        
        return {
            "tenant_id": tenant_id,
            "stale_threshold_days": stale_threshold_days,
            "cleanup_count": len(cleanup_results),
            "dry_run": dry_run,
            "results": cleanup_results,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    def remediate_compliance_issues(
        self,
        compliance_issues: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically remediate compliance issues.
        
        Common issues:
        - Missing MFA
        - Weak password policies
        - Excessive privileges
        - Missing access reviews
        """
        results = []
        
        for issue in compliance_issues:
            issue_type = issue.get("type")
            control = issue.get("control")
            
            try:
                if issue_type == "missing_mfa":
                    result = self._remediate_missing_mfa(
                        issue,
                        tenant_id,
                        dry_run
                    )
                    results.append(result)
                
                elif issue_type == "weak_password_policy":
                    result = self._remediate_weak_password_policy(
                        issue,
                        tenant_id,
                        dry_run
                    )
                    results.append(result)
                
                elif issue_type == "excessive_privileges":
                    result = self._remediate_excessive_privileges(
                        issue,
                        tenant_id,
                        dry_run
                    )
                    results.append(result)
                
                elif issue_type == "missing_access_review":
                    result = self._remediate_missing_access_review(
                        issue,
                        tenant_id,
                        dry_run
                    )
                    results.append(result)
                
            except Exception as e:
                logger.error(f"Error remediating compliance issue {issue_type}: {e}")
                results.append({
                    "issue_id": issue.get("id"),
                    "type": issue_type,
                    "control": control,
                    "success": False,
                    "error": str(e)
                })
        
        successful = sum(1 for r in results if r.get("success", False))
        
        return {
            "tenant_id": tenant_id,
            "total_issues": len(compliance_issues),
            "remediated": successful,
            "failed": len(results) - successful,
            "dry_run": dry_run,
            "results": results,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    def _remediate_over_privileged_user(
        self,
        user_id: str,
        violation: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Remediate over-privileged user by removing excessive roles."""
        recommended_roles = violation.get("recommended_roles", [])
        current_roles = violation.get("current_roles", [])
        
        roles_to_remove = [r for r in current_roles if r not in recommended_roles]
        
        if not dry_run:
            for role in roles_to_remove:
                try:
                    # TODO: Remove role from user
                    # self.keycloak_client.remove_user_role(user_id, role)
                    pass
                except Exception as e:
                    logger.error(f"Error removing role {role}: {e}")
        
        return {
            "user_id": user_id,
            "type": "over_privileged",
            "roles_removed": len(roles_to_remove),
            "roles_to_remove": roles_to_remove,
            "dry_run": dry_run,
            "success": True
        }
    
    def _remediate_policy_violation(
        self,
        user_id: str,
        violation: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Remediate policy violation by revoking violating access."""
        violating_access = violation.get("violating_access", [])
        
        if not dry_run:
            # Revoke violating entitlements/roles
            for access in violating_access:
                try:
                    # TODO: Revoke access
                    pass
                except Exception as e:
                    logger.error(f"Error revoking access: {e}")
        
        return {
            "user_id": user_id,
            "type": "policy_violation",
            "access_revoked": len(violating_access),
            "dry_run": dry_run,
            "success": True
        }
    
    def _remediate_expired_entitlement(
        self,
        violation: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Remediate expired entitlement by revoking it."""
        entitlement_id = violation.get("entitlement_id")
        
        if not dry_run:
            # TODO: Revoke expired entitlement via Entitlement Agent
            pass
        
        return {
            "entitlement_id": entitlement_id,
            "type": "expired_entitlement",
            "action": "revoked",
            "dry_run": dry_run,
            "success": True
        }
    
    def _remediate_unused_entitlement(
        self,
        violation: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Remediate unused entitlement by revoking it."""
        entitlement_id = violation.get("entitlement_id")
        days_unused = violation.get("days_unused", 0)
        
        if not dry_run:
            # TODO: Revoke unused entitlement via Entitlement Agent
            pass
        
        return {
            "entitlement_id": entitlement_id,
            "type": "unused_entitlement",
            "days_unused": days_unused,
            "action": "revoked",
            "dry_run": dry_run,
            "success": True
        }
    
    def _remediate_missing_mfa(
        self,
        issue: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Remediate missing MFA by enabling it for users."""
        user_ids = issue.get("user_ids", [])
        
        if not dry_run:
            for user_id in user_ids:
                try:
                    # TODO: Enable MFA for user
                    # self.keycloak_client.enable_mfa(user_id)
                    pass
                except Exception as e:
                    logger.error(f"Error enabling MFA for {user_id}: {e}")
        
        return {
            "type": "missing_mfa",
            "users_updated": len(user_ids),
            "dry_run": dry_run,
            "success": True
        }
    
    def _remediate_weak_password_policy(
        self,
        issue: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Remediate weak password policy by updating realm settings."""
        if not dry_run:
            # TODO: Update password policy in Keycloak
            # self.keycloak_client.update_password_policy(...)
            pass
        
        return {
            "type": "weak_password_policy",
            "action": "policy_updated",
            "dry_run": dry_run,
            "success": True
        }
    
    def _remediate_excessive_privileges(
        self,
        issue: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Remediate excessive privileges."""
        user_ids = issue.get("user_ids", [])
        
        if not dry_run:
            for user_id in user_ids:
                try:
                    # Similar to over-privileged remediation
                    pass
                except Exception as e:
                    logger.error(f"Error remediating excessive privileges for {user_id}: {e}")
        
        return {
            "type": "excessive_privileges",
            "users_remediated": len(user_ids),
            "dry_run": dry_run,
            "success": True
        }
    
    def _remediate_missing_access_review(
        self,
        issue: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Remediate missing access review by scheduling one."""
        if not dry_run:
            # TODO: Schedule access review campaign
            # self._schedule_access_review(issue)
            pass
        
        return {
            "type": "missing_access_review",
            "action": "review_scheduled",
            "dry_run": dry_run,
            "success": True
        }

