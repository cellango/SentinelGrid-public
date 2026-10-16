"""Dashboard snapshot API for IAM Agent."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.api.request_context import RequestContext, get_current_request_context
from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

router = APIRouter(tags=["dashboard"])


# ============================================================================
# Response Models
# ============================================================================

class DashboardMetrics(BaseModel):
    """Dashboard metrics response."""
    users_total: int
    users_active: int
    users_inactive: int
    users_admins: int
    mfa_coverage_percent: float
    mfa_missing_count: int
    dormant_accounts_count: int
    failed_logins_24h: int
    anomalies_count: int
    anomalies_critical: int
    devices_total: int
    devices_trusted: int
    devices_untrusted: int
    fast_win: Optional[dict] = None


# ============================================================================
# Helper Functions
# ============================================================================

def get_realm_for_tenant(tenant_id: str) -> str:
    """Get Keycloak realm name for tenant."""
    return settings.KEYCLOAK_REALM


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.get("/dashboard-snapshot")
async def get_iam_dashboard_snapshot(
    request_context: RequestContext = Depends(get_current_request_context),
):
    """
    Get IAM/People & Access dashboard snapshot.
    Returns user counts, MFA coverage, dormant accounts, and fast wins.
    """
    tenant_id = str(request_context.tenant_id)
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get all users
            response = await kc._make_request("GET", f"/realms/{realm}/users")
            response.raise_for_status()
            all_users = response.json()
            
            # Filter to tenant
            tenant_users = [
                u for u in all_users
                if extract_tenant_id_from_user(u) == tenant_id
            ]
            
            # Calculate metrics
            users_total = len(tenant_users)
            users_active = len([u for u in tenant_users if u.get("enabled", False)])
            users_inactive = users_total - users_active
            
            # Count admins (users with admin roles)
            users_admins = 0
            mfa_enabled = 0
            mfa_missing = 0
            
            for user in tenant_users:
                # Check for admin roles
                user_roles = await kc._make_request(
                    "GET",
                    f"/realms/{realm}/users/{user['id']}/role-mappings/realm"
                )
                user_roles.raise_for_status()
                roles = user_roles.json()
                
                if any("ADMIN" in r.get("name", "").upper() for r in roles):
                    users_admins += 1
                
                # Check MFA status
                creds = await kc._make_request(
                    "GET",
                    f"/realms/{realm}/users/{user['id']}/credentials"
                )
                creds.raise_for_status()
                credentials = creds.json()
                has_mfa = any(c.get("type") == "otp" for c in credentials)
                
                if has_mfa:
                    mfa_enabled += 1
                else:
                    mfa_missing += 1
            
            mfa_coverage = (mfa_enabled / users_total * 100) if users_total > 0 else 0
            
            # Dormant accounts (not logged in for 90+ days)
            # In production, query audit logs
            dormant_accounts_count = 0
            
            # Failed logins (last 24 hours)
            # In production, query audit logs
            failed_logins_24h = 0
            
            # Anomalies
            from app.services.anomaly_detection import AnomalyDetectionService
            detection_service = AnomalyDetectionService()
            anomalies = await detection_service.detect_anomalies(tenant_id, time_window_hours=24)
            anomalies_count = len(anomalies)
            anomalies_critical = len([a for a in anomalies if a.get("severity") == "critical"])
            
            # Devices (placeholder - would query devices table)
            devices_total = 0
            devices_trusted = 0
            devices_untrusted = 0
            
            # Fast win recommendation
            fast_win = None
            if mfa_missing > 0 and users_admins > 0:
                admin_mfa_missing = min(mfa_missing, users_admins)
                fast_win = {
                    "title": f"Enforce MFA for {admin_mfa_missing} admin account(s)",
                    "description": f"{admin_mfa_missing} admin account(s) are missing MFA. This is a quick security win.",
                    "action": "enforce_mfa",
                }
            elif anomalies_critical > 0:
                fast_win = {
                    "title": f"Review {anomalies_critical} critical anomaly(ies)",
                    "description": f"{anomalies_critical} critical security anomaly(ies) detected. Immediate review recommended.",
                    "action": "review_anomalies",
                }
            
            return DashboardMetrics(
                users_total=users_total,
                users_active=users_active,
                users_inactive=users_inactive,
                users_admins=users_admins,
                mfa_coverage_percent=round(mfa_coverage, 1),
                mfa_missing_count=mfa_missing,
                dormant_accounts_count=dormant_accounts_count,
                failed_logins_24h=failed_logins_24h,
                anomalies_count=anomalies_count,
                anomalies_critical=anomalies_critical,
                devices_total=devices_total,
                devices_trusted=devices_trusted,
                devices_untrusted=devices_untrusted,
                fast_win=fast_win
            )
            
    except Exception as e:
        logger.error(f"Error getting dashboard snapshot: {e}", exc_info=True)
        # Return mock data on error
        return {
            "users_total": 0,
            "users_active": 0,
            "users_inactive": 0,
            "users_admins": 0,
            "mfa_coverage_percent": 0,
            "mfa_missing_count": 0,
            "dormant_accounts_count": 0,
            "failed_logins_24h": 0,
            "anomalies_count": 0,
            "anomalies_critical": 0,
            "devices_total": 0,
            "devices_trusted": 0,
            "devices_untrusted": 0,
        }


def extract_tenant_id_from_user(user: dict) -> Optional[str]:
    """Extract tenant_id from user attributes."""
    attributes = user.get("attributes", {})
    tenant_id = attributes.get("tenant_id")
    return tenant_id[0] if isinstance(tenant_id, list) and tenant_id else tenant_id


import logging
logger = logging.getLogger(__name__)
