"""Connector API endpoints."""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db, get_tenant_db, get_tenant_session
from app.core.security import get_current_tenant, require_connector_request, MAX_SKIP, MAX_LIMIT
from app.models.connector import ConnectorConfig
from app.services.connector_reader import OwnedConnectorReader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"], dependencies=[Depends(require_connector_request)])
oauth_router = APIRouter(prefix="/connectors/oauth", tags=["oauth"], dependencies=[Depends(require_connector_request)])


class ConnectorCreate(BaseModel):
    type: str  # google_workspace, microsoft_entra, okta, aws
    name: str
    credentials: dict
    sync_settings: Optional[dict] = None


class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    credentials: Optional[dict] = None
    sync_settings: Optional[dict] = None
    status: Optional[str] = None


class ConnectorResponse(BaseModel):
    id: str
    tenant_id: str
    type: str
    name: str
    status: str
    last_sync_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.post("", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
def create_connector(
    connector_data: ConnectorCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Create a new connector configuration."""
    # Validate connector type
    valid_types = ["google_workspace", "microsoft_entra", "okta", "aws"]
    if connector_data.type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid connector type. Must be one of: {valid_types}"
        )
    
    # Create connector
    connector = ConnectorConfig(
        tenant_id=UUID(tenant_id),
        type=connector_data.type,
        name=connector_data.name,
        credentials=connector_data.credentials,
        sync_settings=connector_data.sync_settings,
        status="active",
    )
    
    db.add(connector)
    db.commit()
    db.refresh(connector)
    
    return ConnectorResponse(
        id=str(connector.id),
        tenant_id=str(connector.tenant_id),
        type=connector.type,
        name=connector.name,
        status=connector.status,
        last_sync_at=connector.last_sync_at.isoformat() if connector.last_sync_at else None,
        error_message=connector.error_message,
        created_at=connector.created_at.isoformat(),
        updated_at=connector.updated_at.isoformat(),
    )


def get_owned_connector_reader(db: Session = Depends(get_tenant_session, scope="function")) -> OwnedConnectorReader:
    return OwnedConnectorReader(db)


@router.get("", response_model=List[ConnectorResponse])
def list_connectors(skip: int = Query(0, ge=0, le=MAX_SKIP), limit: int = Query(100, ge=1, le=MAX_LIMIT),
    tenant_id: str = Depends(get_current_tenant), reader: OwnedConnectorReader = Depends(get_owned_connector_reader)):
    """Read bounded tenant-owned metadata without loading provider credentials."""
    try:
        return [ConnectorResponse(**row) for row in reader.list_owned(tenant_id, skip, limit)]
    except Exception:
        raise HTTPException(503, "Owned connector store unavailable") from None


@router.get("/{connector_id}", response_model=ConnectorResponse)
def get_connector(connector_id: str, tenant_id: str = Depends(get_current_tenant),
    reader: OwnedConnectorReader = Depends(get_owned_connector_reader)):
    """Read one owned metadata projection; raw provider errors are withheld."""
    try:
        row = reader.get_owned(connector_id, tenant_id)
        result = ConnectorResponse(**row) if row is not None else None
    except Exception:
        raise HTTPException(503, "Owned connector store unavailable") from None
    if result is None:
        raise HTTPException(404, "Connector not found")
    return result


@router.patch("/{connector_id}", response_model=ConnectorResponse)
def update_connector(
    connector_id: str,
    connector_data: ConnectorUpdate,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Update a connector configuration."""
    connector = db.query(ConnectorConfig).filter(
        ConnectorConfig.id == UUID(connector_id),
        ConnectorConfig.tenant_id == UUID(tenant_id)
    ).first()
    
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector {connector_id} not found"
        )
    
    if connector_data.name is not None:
        connector.name = connector_data.name
    if connector_data.credentials is not None:
        connector.credentials = connector_data.credentials
    if connector_data.sync_settings is not None:
        connector.sync_settings = connector_data.sync_settings
    if connector_data.status is not None:
        connector.status = connector_data.status
    
    db.commit()
    db.refresh(connector)
    
    return ConnectorResponse(
        id=str(connector.id),
        tenant_id=str(connector.tenant_id),
        type=connector.type,
        name=connector.name,
        status=connector.status,
        last_sync_at=connector.last_sync_at.isoformat() if connector.last_sync_at else None,
        error_message=connector.error_message,
        created_at=connector.created_at.isoformat(),
        updated_at=connector.updated_at.isoformat(),
    )


@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connector(
    connector_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Delete a connector configuration."""
    connector = db.query(ConnectorConfig).filter(
        ConnectorConfig.id == UUID(connector_id),
        ConnectorConfig.tenant_id == UUID(tenant_id)
    ).first()
    
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector {connector_id} not found"
        )
    
    db.delete(connector)
    db.commit()


@router.post("/{connector_id}/sync", status_code=status.HTTP_200_OK)
def sync_connector(
    connector_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Trigger a manual sync for a connector."""
    from app.services.sync_service import SyncService
    sync_service = SyncService(db)
    result = sync_service.sync_connector(connector_id, tenant_id)
    
    return result


@router.post("/sync/all", status_code=status.HTTP_200_OK)
def sync_all_connectors(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Trigger sync for all active connectors."""
    from app.services.sync_service import SyncService
    sync_service = SyncService(db)
    result = sync_service.sync_all_active_connectors(tenant_id)
    
    return result


@router.post("/{connector_id}/test", status_code=status.HTTP_200_OK)
def test_connector(
    connector_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Test connection for a connector."""
    connector = db.query(ConnectorConfig).filter(
        ConnectorConfig.id == UUID(connector_id),
        ConnectorConfig.tenant_id == UUID(tenant_id)
    ).first()
    
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector {connector_id} not found"
        )
    
    # Test connection based on connector type
    try:
        if connector.type == "google_workspace":
            from app.connectors.google_workspace import GoogleWorkspaceConnector
            connector_instance = GoogleWorkspaceConnector(
                connector.credentials,
                str(connector.tenant_id)
            )
            is_connected = connector_instance.test_connection()
            users = connector_instance.fetch_users() if is_connected else []
            
            return {
                "status": "success" if is_connected else "error",
                "connector_id": str(connector.id),
                "connector_type": connector.type,
                "users_count": len(users) if is_connected else 0,
                "events_available": is_connected,
                "last_event_time": None  # TODO: Get actual last event time
            }
        elif connector.type == "aws":
            # TODO: Implement AWS connection test
            return {
                "status": "success",
                "connector_id": str(connector.id),
                "connector_type": connector.type,
                "message": "AWS connection test not yet implemented"
            }
        else:
            return {
                "status": "error",
                "connector_id": str(connector.id),
                "connector_type": connector.type,
                "error": f"Connection test not implemented for {connector.type}"
            }
    except Exception as e:
        logger.error(f"Failed to test connector {connector_id}: {e}")
        return {
            "status": "error",
            "connector_id": str(connector.id),
            "connector_type": connector.type,
            "error": str(e)
        }


# OAuth endpoints
class OAuthInitRequest(BaseModel):
    provider: str  # google_workspace, microsoft_entra, okta
    tenant_id: str
    redirect_uri: str


class OAuthInitResponse(BaseModel):
    oauth_url: str
    state_token: str


class OAuthCallbackRequest(BaseModel):
    provider: str
    code: str
    state: str


class OAuthCallbackResponse(BaseModel):
    status: str
    connector_id: str
    users_synced: Optional[int] = None
    last_sync: Optional[str] = None


def _require_same_tenant(authenticated_tenant_id: str, requested_tenant_id: str) -> UUID:
    """Reject caller-supplied tenant IDs that do not match authenticated scope."""
    try:
        authenticated = UUID(str(authenticated_tenant_id))
        requested = UUID(str(requested_tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format",
        ) from exc

    if authenticated != requested:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )

    return requested


def resolve_oauth_callback_tenant(request: OAuthCallbackRequest) -> UUID:
    """Legacy in-memory state cannot establish an owned provider callback contract."""
    raise HTTPException(503, "Owned connector OAuth callback contract required")


def get_oauth_callback_tenant_session():
    raise HTTPException(503, "Owned connector OAuth callback contract required")
    yield


@oauth_router.post("/init", response_model=OAuthInitResponse, status_code=status.HTTP_200_OK)
def init_oauth(
    request: OAuthInitRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """
    Initialize OAuth flow for an identity provider.
    
    Returns OAuth URL and state token for the frontend to redirect to.
    """
    from app.services.oauth_service import OAuthService
    oauth_service = OAuthService(db)
    
    try:
        tenant_id = _require_same_tenant(tenant_id, request.tenant_id)
        
        if request.provider == "google_workspace":
            result = oauth_service.init_google_workspace_oauth(
                tenant_id=tenant_id,
                redirect_uri=request.redirect_uri
            )
        elif request.provider == "microsoft_entra":
            result = oauth_service.init_microsoft_oauth(
                tenant_id=tenant_id,
                redirect_uri=request.redirect_uri
            )
        elif request.provider == "okta":
            result = oauth_service.init_okta_oauth(
                tenant_id=tenant_id,
                redirect_uri=request.redirect_uri
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {request.provider}"
            )
        
        return OAuthInitResponse(
            oauth_url=result["oauth_url"],
            state_token=result["state_token"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to initialize OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize OAuth: {str(e)}"
        )


@oauth_router.post("/callback", response_model=OAuthCallbackResponse, status_code=status.HTTP_200_OK)
def oauth_callback(
    request: OAuthCallbackRequest,
    tenant_id: UUID = Depends(resolve_oauth_callback_tenant),
    db: Session = Depends(get_oauth_callback_tenant_session),
):
    """
    Handle OAuth callback from identity provider.
    
    Exchanges authorization code for tokens and creates connector.
    """
    from app.services.oauth_service import OAuthService
    oauth_service = OAuthService(db)
    
    try:
        del tenant_id
        if request.provider == "google_workspace":
            result = oauth_service.handle_google_workspace_callback(
                code=request.code,
                state_token=request.state
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth callback not implemented for {request.provider}"
            )
        
        return OAuthCallbackResponse(
            status=result["status"],
            connector_id=result["connector_id"],
            users_synced=result.get("users_synced"),
            last_sync=result.get("last_sync")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to handle OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle OAuth callback: {str(e)}"
        )
