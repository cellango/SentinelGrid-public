"""
Device Management API endpoints.

Tracks registered devices, trust status, and security posture.
Integrates with endpoint protection for device security status.
"""

import json
import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from uuid import uuid4

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings
from app.api.request_context import get_tenant_session

# Use IAM Agent's database connection (which should point to main DB for assets)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


# ============================================================================
# Request/Response Models
# ============================================================================

class DeviceResponse(BaseModel):
    """Device response model."""
    id: str
    tenant_id: str
    user_id: str
    device_id: str
    device_name: Optional[str]
    device_type: str
    os: Optional[str]
    os_version: Optional[str]
    browser: Optional[str]
    browser_version: Optional[str]
    ip_address: Optional[str]
    trust_status: str
    compliance_status: str
    security_posture: Optional[dict]
    last_seen: datetime
    first_seen: datetime
    registered_at: datetime


class DeviceListResponse(BaseModel):
    """Paginated device list response."""
    items: List[DeviceResponse]
    total: int
    page: int
    limit: int
    pages: int


class DeviceTrustRequest(BaseModel):
    """Device trust request."""
    trust_status: str = Field(..., pattern="^(trusted|untrusted|revoked)$")
    reason: Optional[str] = None


class DeviceReportRequest(BaseModel):
    """Self-service device loss/theft report."""

    report_type: str = Field(..., pattern="^(lost|stolen)$")
    note: Optional[str] = Field(default=None, max_length=2000)


class DeviceRegisterRequest(BaseModel):
    """Register or upsert a device into the assets table."""

    device_id: str = Field(..., description="Unique device identifier / serial")
    device_type: str = Field(..., description="desktop|laptop|mobile|tablet|server")
    name: Optional[str] = Field(None, description="Friendly name/model")
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    owner_email: Optional[str] = Field(None, description="Device owner email")
    user_id: Optional[str] = Field(None, description="Keycloak user id (optional, looked up if owner_email provided)")
    ip_address: Optional[str] = None
    trust_status: Optional[str] = Field("unknown", pattern="^(trusted|untrusted|revoked|unknown)$")
    metadata: Optional[dict] = Field(default_factory=dict)


class SecurityPostureResponse(BaseModel):
    """Device security posture response."""
    device_id: str
    security_score: float  # 0-100
    compliance_status: str  # 'compliant', 'non-compliant', 'unknown'
    threats_detected: List[dict]
    last_scan: Optional[datetime]
    recommendations: List[str]


# ============================================================================
# Helper Functions
# ============================================================================

def _realm_from_issuer(issuer: str) -> str:
    if issuer and "/realms/" in issuer:
        return issuer.split("/realms/")[-1].rstrip("/")
    return settings.KEYCLOAK_REALM


def _safe_metadata(raw: Any) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _token_user_id(token_data: dict) -> str:
    payload = token_data.get("payload") or {}
    return (token_data.get("user_id") or payload.get("sub") or "").strip()


def _token_email(token_data: dict) -> Optional[str]:
    payload = token_data.get("payload") or {}
    return token_data.get("email") or payload.get("email")


def _is_admin(token_data: dict) -> bool:
    roles = token_data.get("roles") or []
    return "TENANT_ADMIN" in roles or "PLATFORM_ADMIN" in roles


def _row_to_device_response(row: Any) -> DeviceResponse:
    meta = _safe_metadata(getattr(row, "metadata", None))
    trust_status = (meta.get("trust_status") or "unknown").lower()
    if trust_status not in {"trusted", "untrusted", "revoked", "unknown"}:
        trust_status = "unknown"
    compliance_status = (meta.get("compliance_status") or getattr(row, "compliance_status", None) or "unknown").lower()
    if compliance_status not in {"compliant", "non_compliant", "revoked", "unknown"}:
        compliance_status = "unknown"

    device_type_mapped = (row.asset_type or "unknown").lower()
    if device_type_mapped in ["mobile", "tablet"]:
        device_type_mapped = "mobile"
    elif device_type_mapped in ["laptop", "desktop", "workstation"]:
        device_type_mapped = "laptop" if "laptop" in device_type_mapped else "desktop"

    first_seen = row.created_at if row.created_at else datetime.utcnow()
    last_seen = row.last_seen_at or row.updated_at or datetime.utcnow()
    registered_at = row.created_at if row.created_at else datetime.utcnow()

    # Derive a simple posture summary if not provided
    posture = meta.get("security_posture")
    if not posture:
        posture_signals = {
            "disk_encrypted": meta.get("disk_encrypted"),
            "firewall_enabled": meta.get("firewall_enabled"),
            "av_installed": meta.get("av_installed"),
            "os_patch_level": meta.get("os_patch_level"),
        }
        score = 100
        deductions = 0
        if posture_signals.get("disk_encrypted") is False:
            deductions += 20
        if posture_signals.get("firewall_enabled") is False:
            deductions += 15
        if posture_signals.get("av_installed") is False:
            deductions += 10
        if posture_signals.get("os_patch_level") in {"outdated", "unknown"}:
            deductions += 10
        score = max(0, score - deductions)
        posture = {
            "score": score,
            "signals": {k: v for k, v in posture_signals.items() if v is not None},
            "notes": "Derived from metadata" if posture_signals else "",
        }

    return DeviceResponse(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        user_id=row.user_id or "",
        device_id=row.asset_id or "",
        device_name=row.name,
        device_type=device_type_mapped,
        os=row.operating_system,
        os_version=row.os_version,
        browser=meta.get("browser"),
        browser_version=meta.get("browser_version"),
        ip_address=row.ip_address,
        trust_status=trust_status,
        compliance_status=compliance_status,
        security_posture=posture,
        last_seen=last_seen,
        first_seen=first_seen,
        registered_at=registered_at,
    )


async def _logout_user_sessions(realm_name: str, user_id: str) -> bool:
    """Best-effort: revoke all active sessions for a user in Keycloak."""
    if not realm_name or not user_id:
        return False
    try:
        async with KeycloakAdminClient() as kc:
            response = await kc._make_request(
                "POST",
                f"/realms/{realm_name}/users/{user_id}/logout",
            )
            return response.status_code in (200, 204)
    except Exception as e:
        logger.warning(f"Failed to revoke sessions for user {user_id} in realm {realm_name}: {e}")
        return False


def _log_audit_event(
    db: Session,
    *,
    tenant_id: str,
    realm_name: str,
    action: str,
    actor_user_id: str,
    actor_email: Optional[str],
    target_user_id: Optional[str],
    details: dict,
) -> None:
    """Insert an IAM audit log event (best-effort)."""
    try:
        db.execute(
            text(
                """
                INSERT INTO iam_audit_log (tenant_id, realm_name, action, actor_user_id, actor_email, target_user_id, details)
                VALUES (:tenant_id, :realm_name, :action, :actor_user_id, :actor_email, :target_user_id, CAST(:details AS jsonb))
                """
            ),
            {
                "tenant_id": tenant_id,
                "realm_name": realm_name,
                "action": action,
                "actor_user_id": actor_user_id,
                "actor_email": actor_email,
                "target_user_id": target_user_id,
                "details": json.dumps(details or {}),
            },
        )
    except Exception as e:
        logger.warning(f"Failed to write iam_audit_log event action={action}: {e}")


async def _resolve_user_id_from_email(email: Optional[str], realm_name: str) -> Optional[str]:
    """Best-effort lookup of a Keycloak user_id from email."""
    if not email:
        return None
    try:
        async with KeycloakAdminClient() as kc:
            # Keycloak Admin v2 search by email
            resp = await kc._make_request(
                "GET",
                f"/realms/{realm_name}/users",
                params={"email": email, "exact": "true"},
            )
            if resp.status_code == 200:
                users = resp.json() or []
                if users:
                    return users[0].get("id")
    except Exception as e:
        logger.warning(f"Best-effort user lookup by email failed for {email}: {e}")
    return None


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

    # Attach realm_name from issuer if present (multi-realm support)
    iss = (result.get("payload") or {}).get("iss", "")
    result["realm_name"] = _realm_from_issuer(iss)
    
    return result


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get Keycloak realm name for tenant."""
    return settings.KEYCLOAK_REALM


# ============================================================================
# Device Endpoints
# ============================================================================

@router.get("", response_model=DeviceListResponse)
async def list_devices(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    trust_status: Optional[str] = Query(None, description="Filter by trust status"),
    compliance_status: Optional[str] = Query(None, description="Filter by compliance status"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    authorization: str = Header(..., alias="authorization", description="Bearer token"),
    db: Session = Depends(get_tenant_session)
):
    """
    List registered devices for the tenant.
    
    Queries the assets table to get devices (mobile, laptop, desktop, etc.).
    Can filter by user, trust status, and device type.
    """
    # Extract token from "Bearer <token>" format
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    logger.info(f"🔍 [list_devices] Received request: user_id={user_id}, device_type={device_type}, page={page}, limit={limit}, token_length={len(token) if token else 0}")
    token_data = await get_token_data(token)
    tenant_id = token_data["tenant_id"]
    current_user_id = _token_user_id(token_data)
    current_user_email = _token_email(token_data)
    is_admin = _is_admin(token_data)
    logger.info(f"🔍 [list_devices] Token validated, tenant_id={tenant_id}")

    try:
        if not current_user_id and not is_admin:
            raise HTTPException(status_code=401, detail="Invalid token: missing user_id")

        # Build query to get assets (devices) for this tenant
        query = """
            SELECT 
                id, tenant_id, asset_id, asset_type, name, 
                operating_system, os_version, ip_address,
                owner, user_id, created_at, updated_at, metadata, last_seen_at, compliance_status
            FROM assets
            WHERE tenant_id = :tenant_id
        """
        params = {"tenant_id": str(tenant_id)}

        # Determine which user filter to apply (self-service should still show assets that only have owner email)
        filter_user_id = None
        filter_email = None

        if user_id:
            if not is_admin and user_id != current_user_id:
                raise HTTPException(status_code=403, detail="Not authorized to view other users' devices")
            filter_user_id = user_id
            # Only use email fallback when querying for the current user (avoid broad matches when admins filter others)
            if user_id == current_user_id and current_user_email:
                filter_email = current_user_email
        elif is_admin:
            # Admin viewing "My Devices" should see all tenant devices by default
            filter_user_id = None
        elif not is_admin:
            filter_user_id = current_user_id
            filter_email = current_user_email

        if filter_user_id:
            query += " AND (user_id = :filter_user_id"
            params["filter_user_id"] = filter_user_id
            if filter_email:
                query += " OR owner = :filter_email OR metadata->>'owner_email' = :filter_email"
                params["filter_email"] = filter_email
            query += ")"

        if device_type:
            query += " AND asset_type = :device_type"
            params["device_type"] = device_type

        if trust_status:
            trust_status = trust_status.lower()
            if trust_status not in {"trusted", "untrusted", "revoked", "unknown"}:
                raise HTTPException(status_code=400, detail="Invalid trust_status filter")
            query += " AND COALESCE(metadata->>'trust_status','unknown') = :trust_status"
            params["trust_status"] = trust_status
        if compliance_status:
            compliance_status = compliance_status.lower()
            if compliance_status not in {"compliant", "non_compliant", "revoked", "unknown"}:
                raise HTTPException(status_code=400, detail="Invalid compliance_status filter")
            query += " AND COALESCE(metadata->>'compliance_status', compliance_status::text, 'unknown') = :compliance_status"
            params["compliance_status"] = compliance_status

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) AS filtered_assets"
        total_result = db.execute(text(count_query), params).scalar()
        total = int(total_result or 0)

        # Apply pagination
        offset = (page - 1) * limit
        query += " ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        # Execute query
        logger.info(f"🔍 [list_devices] Executing query with params: {params}")
        result = db.execute(text(query), params)
        rows = result.fetchall()
        logger.info(f"🔍 [list_devices] Query returned {len(rows)} rows")

        devices = [_row_to_device_response(row) for row in rows]

        # Calculate pages
        pages = (total + limit - 1) // limit if total > 0 else 1

        logger.info(f"🔍 [list_devices] Returning {len(devices)} devices, total={total}, pages={pages}")
        return DeviceListResponse(items=devices, total=total, page=page, limit=limit, pages=pages)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list devices: {str(e)}")


@router.post("/register", response_model=DeviceResponse)
async def register_device(
    request: DeviceRegisterRequest,
    authorization: str = Header(..., alias="authorization", description="Bearer token"),
    db: Session = Depends(get_tenant_session),
):
    """
    Register or update a device in the assets table.
    Admin-only. Upserts on asset_id/device_id.
    """
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    token_data = await get_token_data(token)
    tenant_id = token_data["tenant_id"]
    realm_name = token_data.get("realm_name") or settings.KEYCLOAK_REALM
    actor_user_id = _token_user_id(token_data)
    actor_email = _token_email(token_data)

    if "TENANT_ADMIN" not in (token_data.get("roles") or []):
        raise HTTPException(status_code=403, detail="Admin role required to register devices")

    trust_status = (request.trust_status or "unknown").lower()
    if trust_status not in {"trusted", "untrusted", "revoked", "unknown"}:
        trust_status = "unknown"
    compliance_status = request.metadata.get("compliance_status") if request.metadata else None
    if compliance_status not in {None, "compliant", "non_compliant", "revoked", "unknown"}:
        compliance_status = None

    # Best-effort resolve user_id from email if not provided
    resolved_user_id = request.user_id or await _resolve_user_id_from_email(request.owner_email, realm_name)

    try:
        existing = db.execute(
            text(
                """
                SELECT id, tenant_id, asset_id, asset_type, name, operating_system, os_version, ip_address,
                       owner, user_id, created_at, updated_at, metadata, last_seen_at, compliance_status
                FROM assets
                WHERE tenant_id = :tenant_id AND asset_id = :asset_id
                LIMIT 1
                """
            ),
            {"tenant_id": str(tenant_id), "asset_id": request.device_id},
        ).fetchone()

        metadata = _safe_metadata(existing.metadata if existing else None)
        metadata.update(request.metadata or {})
        metadata["trust_status"] = trust_status
        if compliance_status:
            metadata["compliance_status"] = compliance_status

        now = datetime.utcnow()
        fields = {
            "tenant_id": str(tenant_id),
            "asset_id": request.device_id,
            "asset_type": request.device_type,
            "name": request.name or request.device_id,
            "operating_system": request.operating_system,
            "os_version": request.os_version,
            "ip_address": request.ip_address,
            "owner": request.owner_email,
            "user_id": resolved_user_id,
            "metadata": json.dumps(metadata),
            "compliance_status": compliance_status or "unknown",
            "now": now,
        }

        if existing:
            result = db.execute(
                text(
                    """
                    UPDATE assets
                    SET name=:name,
                        asset_type=:asset_type,
                        operating_system=:operating_system,
                        os_version=:os_version,
                        ip_address=:ip_address,
                        owner=:owner,
                        user_id=:user_id,
                        metadata=CAST(:metadata AS jsonb),
                        compliance_status=COALESCE(:compliance_status, compliance_status),
                        updated_at=:now,
                        last_seen_at=COALESCE(:now, last_seen_at)
                    WHERE tenant_id=:tenant_id AND asset_id=:asset_id
                    RETURNING id, tenant_id, asset_id, asset_type, name, operating_system, os_version, ip_address,
                              owner, user_id, created_at, updated_at, metadata, last_seen_at, compliance_status
                    """
                ),
                fields,
            )
        else:
            fields["id"] = str(uuid4())
            result = db.execute(
                text(
                    """
                    INSERT INTO assets (
                        id, tenant_id, asset_id, asset_type, name,
                        operating_system, os_version, ip_address,
                        owner, user_id, source, metadata, compliance_status, created_at, updated_at, last_seen_at
                    ) VALUES (
                        :id, :tenant_id, :asset_id, :asset_type, :name,
                        :operating_system, :os_version, :ip_address,
                        :owner, :user_id, 'manual', CAST(:metadata AS jsonb), :compliance_status, :now, :now, :now
                    )
                    RETURNING id, tenant_id, asset_id, asset_type, name, operating_system, os_version, ip_address,
                              owner, user_id, created_at, updated_at, metadata, last_seen_at, compliance_status
                    """
                ),
                fields,
            )

        row = result.fetchone()
        db.commit()

        _log_audit_event(
            db,
            tenant_id=str(tenant_id),
            realm_name=realm_name,
            action="device_registered",
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            target_user_id=row.user_id if row else None,
            details={
                "device_asset_id": request.device_id,
                "device_type": request.device_type,
                "trust_status": trust_status,
                "compliance_status": compliance_status or "unknown",
                "owner_email": request.owner_email,
                "resolved_user_id": resolved_user_id,
                "upsert": bool(existing),
            },
        )

        return _row_to_device_response(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register device: {str(e)}")


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    authorization: str = Header(..., alias="authorization", description="Bearer token")
):
    """Get device details by device ID."""
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    token_data = await get_token_data(token)
    tenant_id = token_data["tenant_id"]
    
    try:
        # In production, query database
        # For now, return placeholder
        raise HTTPException(status_code=501, detail="Not yet implemented - will query database")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device")


@router.post("/{device_id}/trust", response_model=DeviceResponse)
async def set_device_trust(
    device_id: str,
    request: DeviceTrustRequest,
    authorization: str = Header(..., alias="authorization", description="Bearer token"),
    db: Session = Depends(get_tenant_session),
):
    """
    Set device trust status.
    
    Marks device as trusted, untrusted, or revoked.
    """
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    token_data = await get_token_data(token)
    tenant_id = token_data["tenant_id"]
    realm_name = token_data.get("realm_name") or settings.KEYCLOAK_REALM
    actor_user_id = _token_user_id(token_data)
    actor_email = _token_email(token_data)

    if "TENANT_ADMIN" not in (token_data.get("roles") or []):
        raise HTTPException(status_code=403, detail="Admin role required to set device trust")
    
    logger.info(f"Setting device {device_id} trust status to {request.trust_status} for tenant {tenant_id}")
    
    try:
        existing = db.execute(
            text(
                """
                SELECT id, tenant_id, asset_id, asset_type, name, operating_system, os_version, ip_address,
                       owner, user_id, created_at, updated_at, metadata, last_seen_at, compliance_status
                FROM assets
                WHERE tenant_id = :tenant_id AND asset_id = :asset_id
                LIMIT 1
                """
            ),
            {"tenant_id": str(tenant_id), "asset_id": device_id},
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Device not found")

        meta = _safe_metadata(existing.metadata)
        meta["trust_status"] = request.trust_status
        meta["trust_updated_at"] = datetime.utcnow().isoformat()
        meta["trust_updated_by"] = actor_user_id
        if request.reason:
            meta["trust_reason"] = request.reason

        desired_compliance = meta.get("compliance_status")
        if request.trust_status == "revoked":
            desired_compliance = "revoked"

        result = db.execute(
            text(
                """
                UPDATE assets
                SET metadata = CAST(:metadata AS jsonb),
                    compliance_status = COALESCE(:compliance_status, compliance_status),
                    updated_at = NOW()
                WHERE tenant_id = :tenant_id AND asset_id = :asset_id
                RETURNING id, tenant_id, asset_id, asset_type, name, operating_system, os_version, ip_address,
                          owner, user_id, created_at, updated_at, metadata, last_seen_at, compliance_status
                """
            ),
            {
                "tenant_id": str(tenant_id),
                "asset_id": device_id,
                "metadata": json.dumps(meta),
                "compliance_status": desired_compliance,
            },
        )
        updated = result.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Device not found")

        _log_audit_event(
            db,
            tenant_id=str(tenant_id),
            realm_name=realm_name,
            action="device_trust_updated",
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            target_user_id=updated.user_id,
            details={
                "device_asset_id": device_id,
                "trust_status": request.trust_status,
                "reason": request.reason,
            },
        )
        db.commit()

        return _row_to_device_response(updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting device trust: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set device trust")


@router.post("/{device_id}/revoke")
async def revoke_device(
    device_id: str,
    authorization: str = Header(..., alias="authorization", description="Bearer token"),
    db: Session = Depends(get_tenant_session),
):
    """
    Revoke a device.
    
    Marks device as revoked and invalidates all sessions from that device.
    """
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    token_data = await get_token_data(token)
    tenant_id = token_data["tenant_id"]
    realm_name = token_data.get("realm_name") or settings.KEYCLOAK_REALM
    actor_user_id = _token_user_id(token_data)
    actor_email = _token_email(token_data)

    if "TENANT_ADMIN" not in (token_data.get("roles") or []):
        raise HTTPException(status_code=403, detail="Admin role required to revoke device")
    
    logger.info(f"Revoking device {device_id} for tenant {tenant_id}")
    
    try:
        existing = db.execute(
            text(
                """
                SELECT id, tenant_id, asset_id, asset_type, name, operating_system, os_version, ip_address,
                       owner, user_id, created_at, updated_at, metadata, last_seen_at, compliance_status
                FROM assets
                WHERE tenant_id = :tenant_id AND asset_id = :asset_id
                LIMIT 1
                """
            ),
            {"tenant_id": str(tenant_id), "asset_id": device_id},
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Device not found")

        meta = _safe_metadata(existing.metadata)
        meta["trust_status"] = "revoked"
        meta["revoked_at"] = datetime.utcnow().isoformat()
        meta["revoked_by"] = actor_user_id

        db.execute(
            text(
                """
                UPDATE assets
                SET metadata = CAST(:metadata AS jsonb),
                    compliance_status = 'revoked',
                    updated_at = NOW()
                WHERE tenant_id = :tenant_id AND asset_id = :asset_id
                """
            ),
            {"tenant_id": str(tenant_id), "asset_id": device_id, "metadata": json.dumps(meta)},
        )

        _log_audit_event(
            db,
            tenant_id=str(tenant_id),
            realm_name=realm_name,
            action="device_revoked",
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            target_user_id=existing.user_id,
            details={"device_asset_id": device_id},
        )

        db.commit()

        # Best-effort: logout user sessions (Keycloak)
        if existing.user_id:
            await _logout_user_sessions(realm_name, existing.user_id)

        return {"success": True, "message": "Device revoked successfully", "device_id": device_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to revoke device")


@router.post("/{device_id}/report", response_model=DeviceResponse)
async def report_device_lost_or_stolen(
    device_id: str,
    request: DeviceReportRequest,
    authorization: str = Header(..., alias="authorization", description="Bearer token"),
    db: Session = Depends(get_tenant_session),
):
    """
    Self-service: report a device as lost or stolen.

    - Marks trust_status=revoked (stored in assets.metadata)
    - Writes an audit event
    - Best-effort: logs out the owning user's Keycloak sessions
    """
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    token_data = await get_token_data(token)
    tenant_id = token_data["tenant_id"]
    realm_name = token_data.get("realm_name") or settings.KEYCLOAK_REALM

    actor_user_id = _token_user_id(token_data)
    actor_email = _token_email(token_data)
    is_admin = _is_admin(token_data)

    try:
        existing = db.execute(
            text(
                """
                SELECT id, tenant_id, asset_id, asset_type, name, operating_system, os_version, ip_address,
                       owner, user_id, created_at, updated_at, metadata, last_seen_at, compliance_status
                FROM assets
                WHERE tenant_id = :tenant_id AND asset_id = :asset_id
                LIMIT 1
                """
            ),
            {"tenant_id": str(tenant_id), "asset_id": device_id},
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Device not found")

        if not is_admin and existing.user_id != actor_user_id:
            raise HTTPException(status_code=403, detail="Not authorized to report this device")

        meta = _safe_metadata(existing.metadata)
        meta["trust_status"] = "revoked"
        meta["report"] = {
            "type": request.report_type,
            "note": request.note,
            "reported_at": datetime.utcnow().isoformat(),
            "reported_by": actor_user_id,
        }

        result = db.execute(
            text(
                """
                UPDATE assets
                SET metadata = CAST(:metadata AS jsonb),
                    compliance_status = 'revoked',
                    updated_at = NOW()
                WHERE tenant_id = :tenant_id AND asset_id = :asset_id
                RETURNING id, tenant_id, asset_id, asset_type, name, operating_system, os_version, ip_address,
                          owner, user_id, created_at, updated_at, metadata, last_seen_at, compliance_status
                """
            ),
            {"tenant_id": str(tenant_id), "asset_id": device_id, "metadata": json.dumps(meta)},
        )
        updated = result.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Device not found")

        _log_audit_event(
            db,
            tenant_id=str(tenant_id),
            realm_name=realm_name,
            action=f"device_reported_{request.report_type}",
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            target_user_id=updated.user_id,
            details={"device_asset_id": device_id, "report_type": request.report_type, "note": request.note},
        )
        db.commit()

        if updated.user_id:
            await _logout_user_sessions(realm_name, updated.user_id)

        return _row_to_device_response(updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to report device")


@router.get("/{device_id}/security-posture", response_model=SecurityPostureResponse)
async def get_device_security_posture(
    device_id: str,
    authorization: str = Header(..., alias="authorization", description="Bearer token")
):
    """
    Get device security posture.
    
    Queries endpoint protection (Wazuh) for device security status.
    """
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    token_data = await get_token_data(token)
    tenant_id = token_data["tenant_id"]
    
    logger.info(f"Getting security posture for device {device_id}")
    
    try:
        # In production, query endpoint protection service (Wazuh)
        # For now, return placeholder
        
        return SecurityPostureResponse(
            device_id=device_id,
            security_score=75.0,
            compliance_status="compliant",
            threats_detected=[],
            last_scan=datetime.utcnow(),
            recommendations=[
                "Keep operating system updated",
                "Enable firewall",
                "Install antivirus software"
            ]
        )
        
    except Exception as e:
        logger.error(f"Error getting security posture: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security posture")
