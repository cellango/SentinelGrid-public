"""
Auto-Remediation Service
Legacy remediation compatibility; effects and old placeholder dry runs are blocked.
"""

from app.services.itdr_service import block_legacy_response

import logging
from typing import List, Dict, Any, Optional

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
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def cleanup_stale_access(
        self,
        stale_threshold_days: int = 90,
        tenant_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def remediate_compliance_issues(
        self,
        compliance_issues: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _remediate_over_privileged_user(
        self,
        user_id: str,
        violation: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _remediate_policy_violation(
        self,
        user_id: str,
        violation: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _remediate_expired_entitlement(
        self,
        violation: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _remediate_unused_entitlement(
        self,
        violation: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _remediate_missing_mfa(
        self,
        issue: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _remediate_weak_password_policy(
        self,
        issue: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _remediate_excessive_privileges(
        self,
        issue: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _remediate_missing_access_review(
        self,
        issue: Dict[str, Any],
        tenant_id: Optional[str],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()

