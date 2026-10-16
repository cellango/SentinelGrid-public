"""
Compliance Reporting API endpoints.

Generates compliance and security reports for auditing.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from datetime import datetime, timedelta
import csv
import io

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ReportRequest(BaseModel):
    """Report generation request."""
    report_type: str  # 'login-history', 'mfa-adoption', 'access-logs'
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    format: str = "csv"  # 'csv' or 'pdf'


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_data(credentials: str) -> dict:
    """Extract and validate token, return token data with tenant_id."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(credentials)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not result.get("tenant_id"):
        raise HTTPException(status_code=403, detail="No tenant_id in token")
    
    return result


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get Keycloak realm name for tenant."""
    return settings.KEYCLOAK_REALM


# ============================================================================
# Report Endpoints
# ============================================================================

@router.get("/login-history")
async def get_login_history_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Generate login history report.
    
    Returns CSV or PDF report of user login activity.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    # Default to last 30 days if not specified
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    try:
        # In production, query audit logs for login events
        # For now, return placeholder CSV
        
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "Timestamp", "User", "Email", "IP Address", "User Agent",
                "Result", "MFA Used", "Device Type"
            ])
            
            # In production, would iterate through actual login events
            # writer.writerow([...])
            
            csv_content = output.getvalue()
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=login-history-{tenant_id}-{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
        else:
            # PDF generation would go here
            raise HTTPException(status_code=501, detail="PDF format not yet implemented")
            
    except Exception as e:
        logger.error(f"Error generating login history report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/mfa-adoption")
async def get_mfa_adoption_report(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Generate MFA adoption report.
    
    Returns CSV or PDF report showing MFA enrollment status by user.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
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
            
            if format == "csv":
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Header
                writer.writerow([
                    "User", "Email", "MFA Enabled", "MFA Type", "Enrolled Date", "Last Used"
                ])
                
                # User data
                for user in tenant_users:
                    # Check MFA status
                    creds = await kc._make_request(
                        "GET",
                        f"/realms/{realm}/users/{user['id']}/credentials"
                    )
                    creds.raise_for_status()
                    credentials = creds.json()
                    
                    mfa_enabled = any(c.get("type") == "otp" for c in credentials)
                    mfa_type = "TOTP" if mfa_enabled else "None"
                    enrolled_date = ""
                    last_used = ""
                    
                    if mfa_enabled:
                        otp_creds = [c for c in credentials if c.get("type") == "otp"]
                        if otp_creds:
                            enrolled_date = otp_creds[0].get("createdDate", "")
                    
                    writer.writerow([
                        user.get("username", ""),
                        user.get("email", ""),
                        "Yes" if mfa_enabled else "No",
                        mfa_type,
                        enrolled_date,
                        last_used
                    ])
                
                csv_content = output.getvalue()
                
                return Response(
                    content=csv_content,
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename=mfa-adoption-{tenant_id}-{datetime.now().strftime('%Y%m%d')}.csv"
                    }
                )
            else:
                raise HTTPException(status_code=501, detail="PDF format not yet implemented")
                
    except Exception as e:
        logger.error(f"Error generating MFA adoption report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/access-logs")
async def get_access_logs_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Generate access logs report.
    
    Returns CSV or PDF report of resource access activity.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    # Default to last 30 days if not specified
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    try:
        # In production, query audit logs for access events
        # For now, return placeholder CSV
        
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "Timestamp", "User", "Resource", "Action", "Result", "IP Address"
            ])
            
            # In production, would iterate through actual access events
            # writer.writerow([...])
            
            csv_content = output.getvalue()
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=access-logs-{tenant_id}-{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
        else:
            raise HTTPException(status_code=501, detail="PDF format not yet implemented")
            
    except Exception as e:
        logger.error(f"Error generating access logs report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


def extract_tenant_id_from_user(user: dict) -> Optional[str]:
    """Extract tenant_id from user attributes."""
    attributes = user.get("attributes", {})
    tenant_id = attributes.get("tenant_id")
    return tenant_id[0] if isinstance(tenant_id, list) and tenant_id else tenant_id

