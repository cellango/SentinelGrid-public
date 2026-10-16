"""
Onboarding API endpoints for customer setup wizard.

Handles:
- Identity Provider (IdP) connections
- Multi-cloud account connections (AWS, Azure, GCP)
- Endpoint agent registration
- Git provider connections
- Onboarding progress tracking
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Dict, Any, List, Generator
from datetime import datetime, timedelta
import logging
import uuid
import json
import re
import hashlib

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
import httpx
from app.api.request_context import RequestContext, get_current_request_context
from sg_core.cloud.registry import (
    canonical_provider_id,
    load_cloud_provider_registry,
    provider_registry_payload,
)
from sg_core.cloud.adapters import provider_has_adapter
from sg_core.cloud.change_requests import (
    CloudChangeRequestError,
    apply_prepared_cloud_change,
    change_request_approval_inputs,
    prepare_cloud_change_apply,
    prepare_cloud_change_approval,
)
# Note: onboarding service module was removed; only use defaults from settings
def get_default_tenant_id() -> str:
    return getattr(settings, "SYSTEM_TENANT", None) or getattr(settings, "DEMO_TENANT", "00000000-0000-0000-0000-000000000000")

# Placeholder service import (no-op if module absent)
try:
    from app.services.onboarding import OnboardingService  # type: ignore
except Exception:
    OnboardingService = None
# Legacy import removed; OnboardingService may not exist in this build.
try:
    from app.services.onboarding import OnboardingService, get_default_tenant_id  # type: ignore
except Exception:
    OnboardingService = None  # type: ignore
    def get_default_tenant_id() -> str:
        return getattr(settings, "SYSTEM_TENANT", None) or getattr(settings, "DEMO_TENANT", "00000000-0000-0000-0000-000000000000")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])
portal_router = APIRouter(prefix="/api/iam-portal/onboarding", tags=["onboarding"])

# Database connection
def _build_session() -> Session:
    if not settings.DB_URL:
        raise HTTPException(status_code=500, detail="Database not configured")

    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_db():
    """Get database session."""
    db = _build_session()
    try:
        yield db
    finally:
        db.close()


def get_onboarding_customer_id(
    request_context: RequestContext = Depends(get_current_request_context),
) -> str:
    """Resolve onboarding customer scope from authenticated request context."""
    return str(request_context.tenant_id)


def get_tenant_session(
    customer_id: str = Depends(get_onboarding_customer_id),
) -> Generator[Session, None, None]:
    """Get a DB session with tenant RLS context applied from onboarding auth state."""
    db = _build_session()
    try:
        db.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": customer_id})
        db.execute(text("SET LOCAL app.is_superadmin = 'false'"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            db.execute(text("RESET app.current_tenant_id"))
            db.execute(text("RESET app.is_superadmin"))
        except Exception:
            pass
        db.close()


# ============================================================================
# Request/Response Models
# ============================================================================

class IdpConnectionRequest(BaseModel):
    """Request to connect an identity provider."""
    idp_type: str = Field(
        ...,
        description=(
            "Identity provider type: google_workspace, microsoft_entra, okta, "
            "keycloak, or sentinelgrid (legacy aliases google and microsoft are accepted)"
        ),
    )
    config: Dict[str, Any] = Field(..., description="IdP-specific configuration (OAuth tokens, client IDs, etc.)")


class IdpConnectionResponse(BaseModel):
    """Response for IdP connection."""
    success: bool
    idp_config_id: Optional[str] = None
    status: str
    message: Optional[str] = None


class CloudConnectionRequest(BaseModel):
    """Request to connect a cloud account."""
    cloud_provider: str = Field(..., description="Cloud provider registry ID or alias")
    account_id: Optional[str] = Field(None, description="Provider account, subscription, project, or resource ID")
    account_name: Optional[str] = None
    integration_method: Optional[str] = Field("terraform", description="terraform, cloudformation, arm_template, deployment_manager, manual")
    monitor_role_arn: Optional[str] = None  # For AWS
    external_id: Optional[str] = None  # For AWS
    service_principal_id: Optional[str] = None  # For Azure/GCP
    service_principal_secret: Optional[str] = None  # For Azure/GCP (will be encrypted)
    metadata: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None  # Flexible config blob (UI-driven)


class AppSecConnectionRequest(BaseModel):
    """Request to connect application security gateway/metadata."""
    gateway_url: str
    api_key: str
    app_id: Optional[str] = None
    openapi_url: Optional[str] = None


class AIShieldConnectionRequest(BaseModel):
    """Request to connect AI Shield (hosted or self)."""
    mode: str = Field(..., description="hosted or self")
    endpoint_url: Optional[str] = None  # hosted
    api_key: Optional[str] = None  # hosted
    gateway_url: Optional[str] = None  # self-hosted
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


class TicketingConnectionRequest(BaseModel):
    """Request to connect ticketing for customer-managed SOC."""
    model_config = ConfigDict(populate_by_name=True)

    provider: str = Field(..., description="internal, jira, servicenow")
    url: Optional[str] = None
    project: Optional[str] = None
    api_key: Optional[str] = None
    issue_type: Optional[str] = Field(
        None,
        alias="issueType",
        description="Issue type or case type created in the downstream workflow",
    )
    assignment_mode: Optional[str] = Field(
        None,
        alias="assignmentMode",
        description="project_default, service_owner, named_owner",
    )
    default_assignee: Optional[str] = Field(
        None,
        alias="defaultAssignee",
        description="Fallback assignee or queue when assignment_mode is named_owner",
    )
    assignee_identifier_type: Optional[str] = Field(
        None,
        alias="assigneeIdentifierType",
        description="account_id, email, username, sys_id",
    )
    auto_create_tickets: Optional[bool] = Field(
        True,
        alias="autoCreateTickets",
        description="Whether SentinelGrid should open tickets automatically for high-signal issues",
    )
    notify_slack: Optional[bool] = Field(
        False,
        alias="notifySlack",
        description="Whether to fan out incident notifications to Slack",
    )
    slack_channel: Optional[str] = Field(
        None,
        alias="slackChannel",
        description="Slack channel name for alert fan-out",
    )
    slack_webhook_url: Optional[str] = Field(
        None,
        alias="slackWebhookUrl",
        description="Slack incoming webhook URL",
    )
    soc_managed: Optional[bool] = Field(
        None,
        alias="socManaged",
        description="True if SentinelGrid manages SOC; false if customer-managed",
    )

class RecheckHealthRequest(BaseModel):
    """Request to re-run health check for a connected component."""
    target: str = Field(..., description="appsec, ai, ticketing, cloud, git, endpoint, idp")


class TicketingAssigneeLookupRequest(BaseModel):
    """Search downstream ticketing users for named-owner routing."""
    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(..., min_length=2, max_length=120, description="Search text for display name, email, or username")
    provider: Optional[str] = Field(None, description="jira or servicenow; falls back to stored ticketing config")
    url: Optional[str] = None
    project: Optional[str] = None
    api_key: Optional[str] = None
    assignee_identifier_type: Optional[str] = Field(
        None,
        alias="assigneeIdentifierType",
        description="account_id, email, username, sys_id",
    )
    limit: int = Field(8, ge=1, le=20, description="Maximum results to return")

class TicketingAssigneeLookupResult(BaseModel):
    """Normalized downstream assignee search result."""
    model_config = ConfigDict(populate_by_name=True)

    value: str
    label: str
    description: Optional[str] = None
    identifier_type: str = Field(..., alias="identifierType")
    identifiers: Dict[str, str] = Field(default_factory=dict)


class TicketingAssigneeLookupResponse(BaseModel):
    """Response payload for assignee lookup."""
    model_config = ConfigDict(populate_by_name=True)

    provider: str
    assignee_identifier_type: str = Field(..., alias="assigneeIdentifierType")
    source: str
    results: List[TicketingAssigneeLookupResult] = Field(default_factory=list)


class LoadEndpointSampleRequest(BaseModel):
    """Request to load a sample endpoint event into OpenSearch for validation."""
    index: Optional[str] = None  # defaults to sg-{tenant}-endpoint-*
    pipeline: Optional[str] = None


class InfrastructureChangeApprovalRequest(BaseModel):
    """Approve a provider-backed infrastructure change request."""
    provider: Optional[str] = None
    admin_ssh_cidrs: Optional[Any] = None
    inputs: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class InfrastructureChangeApplyRequest(BaseModel):
    """Apply an approved provider-backed infrastructure change request."""
    provider: Optional[str] = None
    confirm: bool = True


class CloudConnectionResponse(BaseModel):
    """Response for cloud connection."""
    success: bool
    cloud_account_id: Optional[str] = None
    status: str
    message: Optional[str] = None
    test_connection_result: Optional[Dict[str, Any]] = None
    health: Optional[Dict[str, Any]] = None


LEGACY_CLOUD_CONNECTORS = {"aws", "azure", "gcp"}


def _cloud_provider_has_runtime_connector(provider: str) -> bool:
    return provider in LEGACY_CLOUD_CONNECTORS or provider_has_adapter(provider)


def _cloud_config(request_data: CloudConnectionRequest) -> Dict[str, Any]:
    return dict(request_data.metadata or request_data.config or {})


def _cloud_metadata(request_data: CloudConnectionRequest) -> Dict[str, Any]:
    return dict(request_data.metadata or {})


def _json_secret(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _canonical_cloud_provider(provider_id: str) -> str:
    try:
        registry = load_cloud_provider_registry()
        return canonical_provider_id(provider_id, registry)
    except Exception as exc:
        logger.warning("Cloud provider registry unavailable while resolving %s: %s", provider_id, exc)
        return canonical_provider_id(provider_id, {"providers": {}})


def _normalize_cloud_connection_request(request_data: CloudConnectionRequest) -> CloudConnectionRequest:
    """Map registry-driven config fields onto the legacy connector contract."""

    provider = _canonical_cloud_provider(request_data.cloud_provider)
    cfg = _cloud_config(request_data)
    metadata = _cloud_metadata(request_data)
    updates: Dict[str, Any] = {"cloud_provider": provider}

    if provider == "aws":
        updates["account_id"] = request_data.account_id or cfg.get("account_id")
        updates["monitor_role_arn"] = (
            request_data.monitor_role_arn
            or cfg.get("monitor_role_arn")
            or cfg.get("iam_role_arn")
            or cfg.get("role_arn")
        )
    elif provider == "azure":
        tenant_id = cfg.get("tenant_id") or metadata.get("tenant_id")
        if tenant_id:
            metadata["tenant_id"] = tenant_id
        updates["account_id"] = request_data.account_id or cfg.get("subscription_id") or cfg.get("account_id")
        updates["service_principal_id"] = request_data.service_principal_id or cfg.get("client_id")
        updates["service_principal_secret"] = request_data.service_principal_secret or cfg.get("client_secret")
        updates["metadata"] = metadata
    elif provider == "gcp":
        service_account_key = (
            request_data.service_principal_secret
            or cfg.get("service_account_key")
            or cfg.get("service_account_json")
            or cfg.get("client_secret")
        )
        service_account_email = (
            request_data.service_principal_id
            or cfg.get("service_account_email")
            or cfg.get("client_id")
        )
        project_id = request_data.account_id or cfg.get("project_id") or cfg.get("account_id")
        if service_account_email:
            metadata["service_account_email"] = service_account_email
        if project_id:
            metadata["project_id"] = project_id
        updates["account_id"] = project_id
        updates["service_principal_id"] = service_account_email
        updates["service_principal_secret"] = _json_secret(service_account_key)
        updates["metadata"] = metadata
    return request_data.model_copy(update=updates)


class ExternalIdResponse(BaseModel):
    """Response for external ID generation."""
    external_id: str
    sentinelgrid_account_id: str = Field(default="987654321098", description="SentinelGrid's AWS account ID")

class ArtifactAccessResponse(BaseModel):
    """Tenant-scoped artifact access info."""
    tenant_namespace: str
    ecr_repo: str
    helm_repo: str
    s3_prefix: str
    notes: Optional[str] = None


class StepStatus(BaseModel):
    """Represents the status of a configuration step."""
    id: str
    done: bool
    health: Optional[Dict[str, Any]] = None
    tested_at: Optional[str] = None


class OnboardingStatusResponse(BaseModel):
    """Response for onboarding status."""
    idp_connected: bool
    idp_provider: Optional[str] = None
    cloud_connected: bool
    endpoint_deployed: bool
    git_connected: bool
    appsec_connected: bool = False
    ai_connected: bool = False
    ticketing_connected: bool = False
    onboarding_completed: bool
    next_step: Optional[str] = None  # idp, cloud, endpoint, git, appsec, ai, ticketing, complete
    progress_percentage: int = Field(..., ge=0, le=100)
    services_selected: Optional[Dict[str, Any]] = None
    cloud_health: Optional[Dict[str, Any]] = None
    git_health: Optional[Dict[str, Any]] = None
    appsec_health: Optional[Dict[str, Any]] = None
    ai_health: Optional[Dict[str, Any]] = None
    ticketing_health: Optional[Dict[str, Any]] = None
    # Extended status for resumable/config banners and people readiness
    overall_complete: Optional[bool] = None
    last_incomplete_step_id: Optional[str] = None
    steps: Optional[List[StepStatus]] = None
    access_profile_ready: Optional[bool] = None
    birthright_ready: Optional[bool] = None
    trust_profile: Optional[Dict[str, Any]] = None
    announcements: Optional[List[Dict[str, Any]]] = None
    status_version: Optional[str] = None


class TrustProfileRequest(BaseModel):
    """Request payload for trust and compliance onboarding preferences."""
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = False
    frameworks: List[str] = Field(default_factory=list)
    primary_driver: Optional[str] = Field(
        None,
        alias="primaryDriver",
        description="audit, customer_security_review, renewal_pressure, board_reporting, exploratory",
    )
    target_timeline: Optional[str] = Field(
        None,
        alias="targetTimeline",
        description="30_days, 60_days, 90_days, this_quarter, exploratory",
    )
    needs_questionnaire_support: bool = Field(False, alias="needsQuestionnaireSupport")
    needs_evidence_exports: bool = Field(False, alias="needsEvidenceExports")
    notes: Optional[str] = None


class TrustProfileResponse(BaseModel):
    """Response for trust profile persistence."""
    success: bool
    status: str
    trust_profile: Dict[str, Any] = Field(..., alias="trustProfile")
    message: Optional[str] = None


class EndpointAgentRegistrationRequest(BaseModel):
    """Request to register an endpoint agent."""
    agent_id: str
    agent_type: str = Field(default="endpoint_protection", description="endpoint_protection, cloud_agent, network_sensor")
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    os_arch: Optional[str] = None
    agent_version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EndpointAgentRegistrationResponse(BaseModel):
    """Response for agent registration."""
    success: bool
    agent_id: str
    status: str
    message: Optional[str] = None


def encrypt_secret(secret: str, tenant_id: Optional[str] = None) -> str:
    """
    Store secret in Vault and return a reference path.
    """
    from uuid import uuid4
    from app.services.vault_client import VaultClient

    if not settings.VAULT_TOKEN:
        raise HTTPException(status_code=503, detail="Vault not configured")

    path = f"onboarding/{tenant_id or get_default_tenant_id()}/{uuid4()}"
    VaultClient().write_secret(path, {"value": secret})
    return path


def decrypt_secret(encrypted: str) -> str:
    """
    Retrieve secret from Vault via stored reference.
    """
    from app.services.vault_client import VaultClient

    if not settings.VAULT_TOKEN:
        raise HTTPException(status_code=503, detail="Vault not configured")

    data = VaultClient().read_secret(encrypted)
    if not data or "value" not in data:
        raise HTTPException(status_code=404, detail="Secret not found")
    return data["value"]


def _check_url_health(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    method: str = "GET",
    timeout: float = 5.0,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Basic reachability check for external services with optional auth."""
    import httpx
    try:
        req_method = method.upper()
        resp = httpx.request(
            req_method,
            url,
            headers=headers or {},
            timeout=timeout,
            verify=settings.UPSTREAM_TLS_VERIFY,
            json=body,
        )
        status = resp.status_code
        healthy = 200 <= status < 300
        return {
            "status": "healthy" if healthy else "degraded",
            "http_status": status,
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "latency_ms": int(resp.elapsed.total_seconds() * 1000),
        }
    except Exception as e:
        return {"status": "unreachable", "error": str(e), "checked_at": datetime.utcnow().isoformat() + "Z"}


def _build_api_auth_headers(api_key: Optional[str]) -> Dict[str, str]:
    token = (api_key or "").strip()
    if not token:
        return {}
    if re.match(r"^(basic|bearer)\s+", token, re.IGNORECASE):
        return {"Authorization": token}
    return {"Authorization": f"Bearer {token}"}


def _default_assignee_identifier_type(provider: str) -> str:
    normalized = (provider or "internal").lower()
    if normalized == "jira":
        return "account_id"
    if normalized == "servicenow":
        return "username"
    return "username"


def _step_to_index(step_id: Optional[str]) -> Optional[int]:
    """Map step identifiers to persisted integer codes."""
    mapping = {
        "idp": 1,
        "cloud": 2,
        "endpoint": 3,
        "git": 4,
        "appsec": 5,
        "ai": 6,
        "ticketing": 7,
    }
    return mapping.get(step_id) if step_id else None


def _probe_appsec(cfg: Dict[str, Any]) -> Dict[str, Any]:
    url = cfg.get("gateway_url")
    if not url:
        return {"status": "unknown", "checked_at": datetime.utcnow().isoformat() + "Z"}
    headers = {}
    api_key = cfg.get("api_key")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    # Attempt a health endpoint if present
    health_url = url.rstrip("/") + "/health"
    return _check_url_health(health_url, headers=headers)


def _probe_ai(cfg: Dict[str, Any]) -> Dict[str, Any]:
    url = cfg.get("endpoint_url") or cfg.get("gateway_url")
    if not url:
        return {"status": "unknown", "checked_at": datetime.utcnow().isoformat() + "Z"}
    headers = {}
    api_key = cfg.get("api_key")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    client_secret = cfg.get("client_secret")
    if client_secret:
        headers["X-Client-Secret"] = client_secret
    health_url = url.rstrip("/") + "/health"
    return _check_url_health(health_url, headers=headers)


def _probe_ticketing(cfg: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat() + "Z"
    provider = (cfg.get("provider") or "internal").lower()
    notify_slack = bool(cfg.get("notify_slack") or cfg.get("notifySlack"))
    slack_channel = cfg.get("slack_channel") or cfg.get("slackChannel")
    slack_webhook_url = cfg.get("slack_webhook_url") or cfg.get("slackWebhookUrl")
    assignment_mode = cfg.get("assignment_mode") or cfg.get("assignmentMode") or "service_owner"
    default_assignee = cfg.get("default_assignee") or cfg.get("defaultAssignee")
    assignee_identifier_type = (
        cfg.get("assignee_identifier_type")
        or cfg.get("assigneeIdentifierType")
        or _default_assignee_identifier_type(provider)
    )

    health: Dict[str, Any] = {
        "status": "healthy",
        "checked_at": now,
        "provider": provider,
        "project": cfg.get("project"),
        "issue_type": cfg.get("issue_type") or cfg.get("issueType") or "Incident",
        "assignment_mode": assignment_mode,
        "assignee_identifier_type": assignee_identifier_type,
        "auto_create_tickets": bool(cfg.get("auto_create_tickets", cfg.get("autoCreateTickets", True))),
        "notify_slack": notify_slack,
        "slack_channel": slack_channel,
    }

    if provider == "internal":
        health["message"] = "SentinelGrid internal request workflow is enabled."
    else:
        url = cfg.get("url")
        if not url:
            health["status"] = "unknown"
            health["message"] = "Ticketing URL is missing."
            return health
        headers = _build_api_auth_headers(cfg.get("api_key") or cfg.get("apiKey"))
        health.update(_check_url_health(url, headers=headers))

    warnings: List[str] = []
    if assignment_mode == "named_owner" and not default_assignee:
        warnings.append("Named owner routing requires a default assignee.")
    if assignment_mode == "named_owner" and provider == "jira" and assignee_identifier_type == "email":
        warnings.append("Jira Cloud usually requires an account ID for assignee mapping; email only works on some deployments.")
    if assignment_mode == "named_owner" and provider == "servicenow" and assignee_identifier_type not in {"username", "sys_id"}:
        warnings.append("ServiceNow assignee mapping should use a username or sys_id.")
    if notify_slack:
        if not slack_channel:
            warnings.append("Slack notifications are enabled but no Slack channel is configured.")
        if not slack_webhook_url:
            warnings.append("Slack notifications are enabled but the webhook URL is missing.")
        elif not re.match(r"^https://hooks\.slack\.com/services/", slack_webhook_url):
            warnings.append("Slack webhook URL must use the Slack incoming webhook format.")

    if warnings:
        health["status"] = "degraded"
        health["warnings"] = warnings

    return health


def _probe_idp(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "healthy",
        "checked_at": datetime.utcnow().isoformat() + "Z",
        "provider": cfg.get("idp_type") or cfg.get("provider") or "idp",
    }


def _load_ticketing_lookup_config(progress_id: str, db) -> Dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT ticketing_config
            FROM onboarding_progress
            WHERE customer_id = :customer_id
            LIMIT 1
            """
        ),
        {"customer_id": progress_id},
    ).mappings().fetchone()
    return (row or {}).get("ticketing_config") or {}


def _normalize_ticketing_lookup_config(
    stored_config: Dict[str, Any],
    request_data: TicketingAssigneeLookupRequest,
) -> Dict[str, Any]:
    config = dict(stored_config or {})
    for key in ("provider", "url", "project", "api_key"):
        value = getattr(request_data, key, None)
        if value:
            config[key] = value
    if request_data.assignee_identifier_type:
        config["assignee_identifier_type"] = request_data.assignee_identifier_type
    config["query"] = request_data.query.strip()
    config["limit"] = request_data.limit
    return config


def _resolve_requested_identifier(
    identifiers: Dict[str, str],
    identifier_type: str,
) -> Optional[str]:
    preferred = (identifier_type or "").lower()
    return identifiers.get(preferred) if identifiers else None


def _format_jira_assignee_results(
    users: List[Dict[str, Any]],
    identifier_type: str,
    limit: int,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for user in users:
        identifiers: Dict[str, str] = {}
        if user.get("accountId"):
            identifiers["account_id"] = str(user["accountId"])
        if user.get("emailAddress"):
            identifiers["email"] = str(user["emailAddress"])
        if user.get("name"):
            identifiers["username"] = str(user["name"])
        elif user.get("key"):
            identifiers["username"] = str(user["key"])

        value = _resolve_requested_identifier(identifiers, identifier_type)
        if not value:
            continue

        description_parts: List[str] = []
        if identifiers.get("email"):
            description_parts.append(identifiers["email"])
        if identifiers.get("username") and identifier_type != "username":
            description_parts.append(f"username: {identifiers['username']}")
        if user.get("accountType"):
            description_parts.append(str(user["accountType"]))

        results.append(
            {
                "value": value,
                "label": str(
                    user.get("displayName")
                    or identifiers.get("email")
                    or identifiers.get("username")
                    or value
                ),
                "description": " • ".join(description_parts) or None,
                "identifier_type": identifier_type,
                "identifiers": identifiers,
            }
        )
        if len(results) >= limit:
            break
    return results


def _format_servicenow_assignee_results(
    users: List[Dict[str, Any]],
    identifier_type: str,
    limit: int,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for user in users:
        identifiers: Dict[str, str] = {}
        if user.get("sys_id"):
            identifiers["sys_id"] = str(user["sys_id"])
        if user.get("user_name"):
            identifiers["username"] = str(user["user_name"])
        if user.get("email"):
            identifiers["email"] = str(user["email"])

        value = _resolve_requested_identifier(identifiers, identifier_type)
        if not value:
            continue

        description_parts: List[str] = []
        if identifiers.get("username") and identifier_type != "username":
            description_parts.append(f"user_name: {identifiers['username']}")
        if identifiers.get("email"):
            description_parts.append(identifiers["email"])
        if user.get("active") in {True, "true", "True"}:
            description_parts.append("active")

        results.append(
            {
                "value": value,
                "label": str(
                    user.get("name")
                    or identifiers.get("username")
                    or identifiers.get("email")
                    or value
                ),
                "description": " • ".join(description_parts) or None,
                "identifier_type": identifier_type,
                "identifiers": identifiers,
            }
        )
        if len(results) >= limit:
            break
    return results


async def _lookup_ticketing_assignees(
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    provider = str(config.get("provider") or "internal").lower()
    identifier_type = (
        config.get("assignee_identifier_type")
        or _default_assignee_identifier_type(provider)
    )
    query = str(config.get("query") or "").strip()
    limit = int(config.get("limit") or 8)
    url = str(config.get("url") or "").rstrip("/")
    api_key = config.get("api_key")

    if provider not in {"jira", "servicenow"}:
        raise HTTPException(status_code=400, detail="Assignee lookup is only available for Jira and ServiceNow")
    if not url:
        raise HTTPException(status_code=400, detail="Ticketing URL is required before assignee lookup can run")
    if not api_key:
        raise HTTPException(status_code=400, detail="API token is required before assignee lookup can run")
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Enter at least two characters to search assignees")

    headers = _build_api_auth_headers(api_key)
    timeout = httpx.Timeout(8.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        if provider == "jira":
            project = config.get("project")
            attempts = []
            if project:
                attempts.extend(
                    [
                        (
                            f"{url}/rest/api/3/user/assignable/search",
                            {"query": query, "project": project, "maxResults": limit},
                        ),
                        (
                            f"{url}/rest/api/2/user/assignable/search",
                            {"query": query, "project": project, "maxResults": limit},
                        ),
                    ]
                )
            attempts.extend(
                [
                    (f"{url}/rest/api/3/user/search", {"query": query, "maxResults": limit}),
                    (f"{url}/rest/api/2/user/search", {"query": query, "maxResults": limit}),
                ]
            )

            last_response = None
            for endpoint, params in attempts:
                response = await client.get(endpoint, headers=headers, params=params)
                last_response = response
                if response.status_code == 404:
                    continue
                if response.status_code in {401, 403}:
                    raise HTTPException(status_code=400, detail="Jira assignee lookup failed authentication. Check the API token.")
                if response.status_code >= 400:
                    detail = response.text.strip() or f"Jira returned HTTP {response.status_code}"
                    raise HTTPException(status_code=400, detail=f"Jira assignee lookup failed: {detail}")
                payload = response.json()
                users = payload if isinstance(payload, list) else payload.get("values") or payload.get("users") or []
                return _format_jira_assignee_results(users, identifier_type, limit)

            if last_response is not None:
                raise HTTPException(status_code=400, detail="Could not find a compatible Jira user lookup endpoint. Check the Jira base URL.")
            return []

        response = await client.get(
            f"{url}/api/now/table/sys_user",
            headers=headers,
            params={
                "sysparm_query": f"active=true^nameLIKE{query}^ORuser_nameLIKE{query}^ORemailLIKE{query}",
                "sysparm_limit": str(limit),
                "sysparm_fields": "sys_id,name,user_name,email,active",
            },
        )
        if response.status_code in {401, 403}:
            raise HTTPException(status_code=400, detail="ServiceNow assignee lookup failed authentication. Check the API token.")
        if response.status_code == 404:
            raise HTTPException(status_code=400, detail="Could not find the ServiceNow sys_user API. Check the instance URL.")
        if response.status_code >= 400:
            detail = response.text.strip() or f"ServiceNow returned HTTP {response.status_code}"
            raise HTTPException(status_code=400, detail=f"ServiceNow assignee lookup failed: {detail}")

        payload = response.json() or {}
        users = payload.get("result") or []
        return _format_servicenow_assignee_results(users, identifier_type, limit)


def _to_iso8601(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _get_endpoint_agent_health(customer_id: str, db) -> Dict[str, Any]:
    """Return truthful endpoint rollout status from the tenant's registered agent state."""
    now = datetime.utcnow()
    row = db.execute(
        text("""
            SELECT agent_id, hostname, status, registered_at, last_seen_at, agent_version
            FROM customer_endpoint_agents
            WHERE customer_id = :customer_id
            ORDER BY COALESCE(last_seen_at, registered_at) DESC NULLS LAST
            LIMIT 1
        """),
        {"customer_id": customer_id},
    ).mappings().fetchone()

    if not row:
        return {
            "status": "pending",
            "checked_at": now.isoformat() + "Z",
            "message": "No endpoint agent is registered for this tenant yet. Deploy the agent and re-run validation.",
        }

    registered_at = row.get("registered_at")
    last_seen_at = row.get("last_seen_at")
    agent_status = str(row.get("status") or "").lower()
    checked_at = _to_iso8601(last_seen_at) or _to_iso8601(registered_at) or now.isoformat() + "Z"

    health = {
        "status": "healthy",
        "checked_at": checked_at,
        "agent_id": row.get("agent_id"),
        "hostname": row.get("hostname"),
        "agent_version": row.get("agent_version"),
        "registered_at": _to_iso8601(registered_at),
        "last_seen_at": _to_iso8601(last_seen_at),
    }

    if agent_status and agent_status != "active":
        health["status"] = "degraded"
        health["message"] = f"Endpoint agent is registered but currently reports status '{agent_status}'."
        return health

    if isinstance(last_seen_at, datetime) and now - last_seen_at > timedelta(hours=24):
        health["status"] = "degraded"
        health["message"] = "Endpoint agent is registered but has not checked in during the last 24 hours."
        return health

    health["message"] = "Endpoint agent is registered and reporting for this tenant."
    return health


def _tenant_namespace_from_slug(tenant_slug: str) -> str:
    """Derive a short tenant namespace from slug."""
    if not tenant_slug:
        return "tenant"
    return tenant_slug.split("-")[0] or tenant_slug[:8]


def _artifact_endpoints(namespace: str):
    ecr = f"{settings.ARTIFACT_ECR_ACCOUNT_ID}.dkr.ecr.{settings.ARTIFACT_ECR_REGION}.amazonaws.com/{namespace}/agent"
    helm = f"{settings.ARTIFACT_HELM_BASE_URL.rstrip('/')}/{namespace}"
    s3 = f"s3://{settings.ARTIFACT_S3_BUCKET}/{namespace}/artifacts/"
    return ecr, helm, s3


def _get_primary_tenant_id(customer_id: Optional[str], db):
    """
    Resolve a tenant_id for the given customer. Falls back to the oldest tenant for the customer.
    """
    if not customer_id:
        return None
    row = db.execute(
        text(
            """
            SELECT t.id
            FROM tenants t
            JOIN organizations o ON o.id = t.organization_id
            JOIN customers c ON c.id = o.customer_id
            WHERE c.id = :cid
            ORDER BY t.created_at ASC
            LIMIT 1
            """
        ),
        {"cid": customer_id},
    ).first()
    return row[0] if row else None


def _resolve_progress_key(customer_id: str, db) -> str:
    """
    Resolve the identifier used for onboarding_progress:
    - Prefer existing onboarding_progress record keyed by customer_id.
    - Fallback to tenant.id when the provided value matches a tenant id or slug (demo/system tenants).
    - Otherwise return the original customer_id.
    """
    if not customer_id:
        return customer_id

    existing = db.execute(
        text("SELECT 1 FROM onboarding_progress WHERE customer_id = :cid LIMIT 1"),
        {"cid": customer_id},
    ).fetchone()
    if existing:
        return customer_id

    tenant_row = db.execute(
        text("SELECT id FROM tenants WHERE id = :cid OR slug = :cid LIMIT 1"),
        {"cid": customer_id},
    ).first()
    if tenant_row:
        return str(tenant_row[0])

    # Last resort: if only one onboarding_progress row exists, reuse its key (demo/system local dev)
    progress_count_row = db.execute(text("SELECT COUNT(*) FROM onboarding_progress")).first()
    if progress_count_row and progress_count_row[0] == 1:
        solo_progress = db.execute(
            text("SELECT customer_id FROM onboarding_progress LIMIT 1")
        ).first()
        if solo_progress:
            return str(solo_progress[0])

    return customer_id


def _infer_existing_connections(db, progress_id: str) -> Dict[str, bool]:
    """
    Infer existing connections (idp/cloud/git) from persisted tables for backfill.
    """
    inferred = {"idp": False, "cloud": False, "git": False}
    try:
        idp_row = db.execute(
            text("SELECT 1 FROM customer_idp_config WHERE customer_id = :cid LIMIT 1"),
            {"cid": progress_id},
        ).first()
        if idp_row:
            inferred["idp"] = True
    except Exception:
        pass
    try:
        cloud_row = db.execute(
            text("SELECT 1 FROM customer_cloud_accounts WHERE customer_id = :cid LIMIT 1"),
            {"cid": progress_id},
        ).first()
        if cloud_row:
            inferred["cloud"] = True
    except Exception:
        pass
    try:
        git_row = db.execute(
            text("SELECT 1 FROM customer_git_providers WHERE customer_id = :cid LIMIT 1"),
            {"cid": progress_id},
        ).first()
        if git_row:
            inferred["git"] = True
    except Exception:
        pass
    return inferred


def _normalize_choice_token(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    token = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    return token or None


def _normalize_idp_type(value: Optional[str]) -> Optional[str]:
    token = _normalize_choice_token(value)
    if token is None:
        return None
    aliases = {
        "google": "google_workspace",
        "google_workspace": "google_workspace",
        "g_suite": "google_workspace",
        "gsuite": "google_workspace",
        "googleworkspace": "google_workspace",
        "microsoft": "microsoft_entra",
        "microsoft_entra": "microsoft_entra",
        "microsoft_365": "microsoft_entra",
        "office_365": "microsoft_entra",
        "azure_ad": "microsoft_entra",
        "azuread": "microsoft_entra",
        "entra": "microsoft_entra",
        "okta": "okta",
        "keycloak": "keycloak",
        "sentinelgrid": "sentinelgrid",
    }
    return aliases.get(token, token)


def _load_latest_idp_provider(progress_id: str, db) -> Optional[str]:
    row = db.execute(
        text(
            """
            SELECT idp_type
            FROM customer_idp_config
            WHERE customer_id = :customer_id
            ORDER BY connected_at DESC NULLS LAST, updated_at DESC NULLS LAST, created_at DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"customer_id": progress_id},
    ).fetchone()
    if not row:
        return None
    return _normalize_idp_type(row[0])


def _normalize_framework_token(value: Optional[str]) -> Optional[str]:
    token = _normalize_choice_token(value)
    if token is None:
        return None
    aliases = {
        "soc_2": "soc2",
        "soc2": "soc2",
        "hipaa": "hipaa",
        "pci": "pci_dss",
        "pci_dss": "pci_dss",
        "iso_27001": "iso27001",
        "iso27001": "iso27001",
        "customer_questionnaire": "customer_questionnaires",
        "customer_questionnaires": "customer_questionnaires",
    }
    return aliases.get(token, token)


def _normalize_trust_profile(raw_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize trust profile payload for consistent storage and UI prompts."""
    profile = raw_profile or {}
    raw_frameworks = profile.get("frameworks") or []
    frameworks: List[str] = []
    for item in raw_frameworks:
        token = _normalize_framework_token(str(item))
        if token and token not in frameworks:
            frameworks.append(token)

    primary_driver = _normalize_choice_token(profile.get("primaryDriver") or profile.get("primary_driver"))
    target_timeline = _normalize_choice_token(profile.get("targetTimeline") or profile.get("target_timeline"))
    notes = (profile.get("notes") or "").strip() or None
    needs_questionnaire_support = bool(
        profile.get("needsQuestionnaireSupport", profile.get("needs_questionnaire_support", False))
    )
    needs_evidence_exports = bool(
        profile.get("needsEvidenceExports", profile.get("needs_evidence_exports", False))
    )

    enabled = bool(profile.get("enabled"))
    if frameworks or primary_driver or target_timeline or needs_questionnaire_support or needs_evidence_exports or notes:
        enabled = True

    return {
        "enabled": enabled,
        "frameworks": frameworks,
        "primaryDriver": primary_driver,
        "targetTimeline": target_timeline,
        "needsQuestionnaireSupport": needs_questionnaire_support,
        "needsEvidenceExports": needs_evidence_exports,
        "notes": notes,
    }


def _trust_profile_incomplete_reasons(trust_profile: Optional[Dict[str, Any]]) -> List[str]:
    profile = _normalize_trust_profile(trust_profile)
    if not profile.get("enabled"):
        return []

    reasons: List[str] = []
    if not profile.get("frameworks"):
        reasons.append("frameworks")
    if not profile.get("primaryDriver"):
        reasons.append("primary_driver")
    if not profile.get("targetTimeline"):
        reasons.append("target_timeline")
    if not (
        profile.get("needsQuestionnaireSupport") or profile.get("needsEvidenceExports")
    ):
        reasons.append("outputs")
    return reasons


def _build_trust_announcements(trust_profile: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    profile = _normalize_trust_profile(trust_profile)
    if not profile.get("enabled"):
        return []

    missing = set(_trust_profile_incomplete_reasons(profile))
    if not missing:
        return []

    announcements: List[Dict[str, Any]] = []
    if "frameworks" in missing:
        announcements.append({
            "id": "trust-scope",
            "title": "Define your trust scope",
            "body": "Choose the frameworks or questionnaire pressure that matter first so reporting and evidence prompts match your actual trust motion.",
            "level": "warning",
        })
    elif "primary_driver" in missing or "target_timeline" in missing:
        announcements.append({
            "id": "trust-priority",
            "title": "Capture your trust timeline",
            "body": "Tell SentinelGrid whether this is for an audit, customer review, or renewal pressure, and when the first deliverable is due.",
            "level": "info",
        })

    if "outputs" in missing:
        announcements.append({
            "id": "trust-outputs",
            "title": "Set reporting outputs",
            "body": "Choose whether you need questionnaire support, evidence exports, or both so the first-week guidance points at the right reporting workflow.",
            "level": "info",
        })
    return announcements


def _status_version_hash(
    steps_payload: List[StepStatus],
    access_ready: bool,
    birthright_ready: bool,
    onboarding_completed: bool,
    trust_profile: Optional[Dict[str, Any]] = None,
    idp_provider: Optional[str] = None,
) -> str:
    raw = json.dumps({
        "steps": [{ "id": s.id, "done": s.done, "status": (s.health or {}).get("status") } for s in steps_payload],
        "access": access_ready,
        "birthright": birthright_ready,
        "completed": onboarding_completed,
        "trust": _normalize_trust_profile(trust_profile),
        "idp_provider": _normalize_idp_type(idp_provider),
    }, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """
    Get onboarding progress status for the current customer.
    """
    try:
        progress_id = _resolve_progress_key(customer_id, db)
        try:
            db.rollback()
        except Exception:
            pass
        default_services = {
            "cloud": True,
            "git": True,
            "appsec": True,
            "aiShield": "hosted",
            "socManaged": False,  # customer-managed SOC -> ticketing step required
        }
        
        # Get onboarding progress (including extended steps/config/health)
        result = db.execute(
            text("""
                SELECT 
                    step_idp_completed,
                    step_cloud_completed,
                    step_endpoint_completed,
                    step_git_completed,
                    onboarding_completed,
                    step_appsec_completed,
                    step_ai_completed,
                    step_ticketing_completed,
                    services_selected,
                    appsec_health,
                    ai_health,
                    ticketing_health,
                    cloud_health
                FROM onboarding_progress
                WHERE customer_id = :customer_id
            """),
            {"customer_id": progress_id}
        ).mappings().fetchone()
        
        if not result:
            # Create initial progress record
            try:
                services_selected_json = json.dumps(default_services)
                db.execute(
                    text("""
                        INSERT INTO onboarding_progress (
                            customer_id,
                            services_selected,
                            onboarding_completed,
                            step_idp_completed,
                            step_cloud_completed,
                            step_endpoint_completed,
                            step_git_completed
                        ) VALUES (
                            :customer_id,
                            CAST(:services_selected AS jsonb),
                            false,
                            false,
                            false,
                            false,
                            false
                        )
                        ON CONFLICT (customer_id) DO NOTHING
                    """),
                    {"customer_id": progress_id, "services_selected": services_selected_json},
                )
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to seed onboarding_progress for {progress_id}: {e}")

            result = db.execute(
                text("""
                    SELECT 
                        step_idp_completed,
                        step_cloud_completed,
                        step_endpoint_completed,
                        step_git_completed,
                        onboarding_completed,
                        step_appsec_completed,
                        step_ai_completed,
                        step_ticketing_completed,
                        services_selected,
                        appsec_health,
                        ai_health,
                        ticketing_health,
                        cloud_health
                    FROM onboarding_progress
                    WHERE customer_id = :customer_id
                """),
                {"customer_id": progress_id}
            ).mappings().fetchone()

            if not result:
                # Should not happen, but keep a safe fallback
                result = {
                    "step_idp_completed": False,
                    "step_cloud_completed": False,
                    "step_endpoint_completed": False,
                    "step_git_completed": False,
                    "onboarding_completed": False,
                    "step_appsec_completed": False,
                    "step_ai_completed": False,
                    "step_ticketing_completed": False,
                    "services_selected": default_services,
                    "appsec_health": None,
                    "ai_health": None,
                    "ticketing_health": None,
                    "cloud_health": None,
                }
        
        idp_connected = result.get("step_idp_completed") or False
        cloud_connected = result.get("step_cloud_completed") or False
        endpoint_deployed = result.get("step_endpoint_completed") or False
        git_connected = result.get("step_git_completed") or False
        onboarding_completed = result.get("onboarding_completed") or False
        step_appsec = result.get("step_appsec_completed") or False
        step_ai = result.get("step_ai_completed") or False
        step_ticketing = result.get("step_ticketing_completed") or False
        services_selected_raw = result.get("services_selected")
        services_selected = services_selected_raw
        appsec_health = result.get("appsec_health")
        ai_health = result.get("ai_health")
        ticketing_health = result.get("ticketing_health")
        cloud_health = result.get("cloud_health")
        git_health = None
        endpoint_health = None
        # Infer existing connections for backfill (demo/system tenants)
        inferred = _infer_existing_connections(db, progress_id)
        if not idp_connected and inferred.get("idp"):
            idp_connected = True
        if not cloud_connected and inferred.get("cloud"):
            cloud_connected = True
        if not git_connected and inferred.get("git"):
            git_connected = True
        # Pull latest git provider health (from metadata) if available
        git_row = db.execute(
            text("""
                SELECT metadata
                FROM customer_git_providers
                WHERE customer_id = :customer_id
                ORDER BY connected_at DESC
                LIMIT 1
            """),
            {"customer_id": progress_id}
        ).fetchone()
        if git_row and git_row[0]:
            meta = git_row[0]
            git_health = meta.get("health") or meta.get("test_result")
            if git_health and git_health.get("success"):
                git_connected = True

        # Normalize services_selected to dict
        if services_selected and isinstance(services_selected, str):
            try:
                services_selected = json.loads(services_selected)
            except Exception:
                services_selected = None

        # Apply defaults for any missing keys so required steps stay consistent
        merged_services = {**default_services, **(services_selected or {})}
        if merged_services.get("aiShield") in (None, ""):
            merged_services["aiShield"] = default_services["aiShield"]
        if merged_services.get("socManaged") is None:
            merged_services["socManaged"] = default_services["socManaged"]
        trust_profile_raw = merged_services.get("trustProfile")
        trust_profile = _normalize_trust_profile(trust_profile_raw if isinstance(trust_profile_raw, dict) else {})
        if trust_profile_raw is not None or trust_profile.get("enabled"):
            merged_services["trustProfile"] = trust_profile
        idp_provider = _load_latest_idp_provider(progress_id, db) or _normalize_idp_type(
            merged_services.get("idpProvider")
        )
        if idp_provider:
            merged_services["idpProvider"] = idp_provider
        elif idp_connected:
            # SentinelGrid identity is the safest fallback when the wizard marked identity complete
            # but no external provider record exists yet (for example in local/demo flows).
            merged_services["idpProvider"] = "sentinelgrid"
            idp_provider = "sentinelgrid"
        services_selected = merged_services

        # Best-effort persist so subsequent calls stay consistent
        if services_selected_raw != services_selected:
            try:
                db.execute(
                    text("""
                        UPDATE onboarding_progress
                        SET services_selected = :services_selected::jsonb, updated_at = NOW()
                        WHERE customer_id = :customer_id
                    """),
                    {"services_selected": json.dumps(services_selected), "customer_id": progress_id},
                )
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist normalized services_selected for onboarding: {e}")

        appsec_connected = step_appsec or ((appsec_health or {}).get("status") == "healthy")
        ai_connected = step_ai or ((ai_health or {}).get("status") == "healthy")
        ticketing_connected = (ticketing_health or {}).get("status") == "healthy"
        if cloud_health:
            cloud_connected = cloud_connected or (cloud_health.get("success") is True)

        services = services_selected or {}
        cloud_required = services.get("cloud", True) is not False
        git_required = services.get("git", True) is not False
        endpoint_required = cloud_required  # Pair endpoint with cloud by default
        if endpoint_required or endpoint_deployed:
            endpoint_health = _get_endpoint_agent_health(progress_id, db)
            endpoint_deployed = (endpoint_health or {}).get("status") == "healthy"

        # Determine required steps based on services_selected; default cloud+endpoint+git are required unless explicitly disabled
        appsec_required = bool(services.get("appsec"))
        ai_required = bool(services.get("aiShield"))
        ticketing_required = services.get("socManaged") is False

        ordered = []
        ordered.append(("idp", idp_connected, None))
        if cloud_required:
            ordered.append(("cloud", cloud_connected, cloud_health))
        if endpoint_required:
            ordered.append(("endpoint", endpoint_deployed, endpoint_health))
        if git_required:
            ordered.append(("git", git_connected, git_health))
        if appsec_required:
            ordered.append(("appsec", appsec_connected, appsec_health))
        if ai_required:
            ordered.append(("ai", ai_connected, ai_health))
        if ticketing_required:
            ordered.append(("ticketing", ticketing_connected, ticketing_health))

        next_step = "complete"
        last_incomplete_step_id = None
        for sid, done, _ in ordered:
            if not done:
                next_step = sid
                last_incomplete_step_id = sid
                break

        # Calculate progress percentage using required steps
        steps_all = [done for (_, done, _) in ordered]
        total_steps = len(steps_all) or 1
        steps_completed = sum(1 for s in steps_all if s)
        progress_percentage = int((steps_completed / total_steps) * 100)

        # People & Access readiness (default access profile + birthright rule)
        access_profile_ready = False
        birthright_ready = False
        try:
            tenant_id = _get_primary_tenant_id(customer_id, db) or db.execute(
                text("SELECT id FROM tenants WHERE id = :pid OR slug = :pid LIMIT 1"),
                {"pid": progress_id},
            ).scalar()
            if tenant_id:
                ap_row = db.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT 1 FROM access_profiles
                            WHERE tenant_id = :tenant_id AND is_default = true
                        )
                    """),
                    {"tenant_id": tenant_id}
                ).fetchone()
                if ap_row:
                    access_profile_ready = bool(ap_row[0])
                br_row = db.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT 1 FROM birthright_rules
                            WHERE tenant_id = :tenant_id
                        )
                    """),
                    {"tenant_id": tenant_id}
                ).fetchone()
                if br_row:
                    birthright_ready = bool(br_row[0])
        except Exception as e:
            logger.warning(f"Failed to compute People & Access readiness: {e}")

        # Build step payload for UI consumption (include health/tested_at if present)
        steps_payload: List[StepStatus] = []
        for sid, done, health in ordered:
            tested_at = None
            if isinstance(health, dict):
                tested_at = health.get("checked_at") or health.get("tested_at")
            steps_payload.append(StepStatus(id=sid, done=done, health=health, tested_at=tested_at))

        required_steps_done = all(steps_all) if steps_all else False
        overall_complete = bool(onboarding_completed or (required_steps_done and access_profile_ready and birthright_ready))

        # Backfill onboarding_progress if inferred connections changed
        fields_to_update = []
        params = {"customer_id": progress_id}
        if not result.get("step_idp_completed") and inferred.get("idp"):
            fields_to_update.append("step_idp_completed = true")
            fields_to_update.append("step_idp_completed_at = COALESCE(step_idp_completed_at, NOW())")
        if not result.get("step_cloud_completed") and inferred.get("cloud"):
            fields_to_update.append("step_cloud_completed = true")
            fields_to_update.append("step_cloud_completed_at = COALESCE(step_cloud_completed_at, NOW())")
        if not result.get("step_git_completed") and inferred.get("git"):
            fields_to_update.append("step_git_completed = true")
            fields_to_update.append("step_git_completed_at = COALESCE(step_git_completed_at, NOW())")
        if fields_to_update:
            update_sql = f"UPDATE onboarding_progress SET {', '.join(fields_to_update)}, updated_at = NOW() WHERE customer_id = :customer_id"
            try:
                db.execute(text(update_sql), params)
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to backfill onboarding_progress for {progress_id}: {e}")

        # Persist resume pointer for cross-device consistency
        try:
            if last_incomplete_step_id:
                step_idx = _step_to_index(last_incomplete_step_id)
                db.execute(
                    text("""
                        UPDATE onboarding_progress
                        SET last_accessed_step = :step, updated_at = NOW()
                        WHERE customer_id = :customer_id
                    """),
                    {"step": step_idx or 1, "customer_id": progress_id},
                )
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist resume pointer for {progress_id}: {e}")

        # Build announcements (lightweight, non-intrusive)
        announcements: List[Dict[str, Any]] = []
        if not access_profile_ready or not birthright_ready:
            announcements.append({
                "id": "people-access-readiness",
                "title": "Finish People & Access",
                "body": "Create a default access profile and at least one birthright rule so joiners get day-one access.",
                "level": "info",
            })
        if not overall_complete:
            announcements.append({
                "id": "config-incomplete",
                "title": "Complete your configuration",
                "body": "You still have setup steps pending. Resume where you left off.",
                "level": "warning",
            })
        announcements.extend(_build_trust_announcements(trust_profile))

        status_version = _status_version_hash(
            steps_payload,
            access_profile_ready,
            birthright_ready,
            onboarding_completed,
            trust_profile,
            idp_provider,
        )

        return OnboardingStatusResponse(
            idp_connected=idp_connected,
            idp_provider=idp_provider,
            cloud_connected=cloud_connected,
            endpoint_deployed=endpoint_deployed,
            git_connected=git_connected,
            appsec_connected=appsec_connected,
            ai_connected=ai_connected,
            ticketing_connected=ticketing_connected,
            onboarding_completed=onboarding_completed,
            next_step=next_step,
            progress_percentage=progress_percentage,
            cloud_health=cloud_health,
            git_health=git_health,
            services_selected=services_selected,
            appsec_health=appsec_health,
            ai_health=ai_health,
            ticketing_health=ticketing_health,
            overall_complete=overall_complete,
            last_incomplete_step_id=last_incomplete_step_id,
            steps=steps_payload,
            access_profile_ready=access_profile_ready,
            birthright_ready=birthright_ready,
            trust_profile=trust_profile,
            announcements=announcements,
            status_version=status_version,
        )
        
    except Exception as e:
        logger.error(f"Error getting onboarding status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get onboarding status: {str(e)}")


@router.post("/trust-profile", response_model=TrustProfileResponse)
async def save_trust_profile(
    request_data: TrustProfileRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session),
):
    """Persist trust and compliance onboarding preferences."""
    try:
        progress_id = _resolve_progress_key(customer_id, db)
        trust_profile = _normalize_trust_profile(request_data.model_dump(by_alias=True))
        services_json = json.dumps({"trustProfile": trust_profile})

        db.execute(
            text("""
                INSERT INTO onboarding_progress (customer_id, services_selected, updated_at)
                VALUES (:customer_id, CAST(:services_selected AS jsonb), NOW())
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    services_selected = COALESCE(onboarding_progress.services_selected, '{}'::jsonb) || CAST(:services_selected AS jsonb),
                    updated_at = NOW()
            """),
            {
                "customer_id": progress_id,
                "services_selected": services_json,
            },
        )
        db.commit()

        return TrustProfileResponse(
            success=True,
            status="saved",
            trustProfile=trust_profile,
            message="Trust and compliance preferences saved",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving trust profile: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save trust profile: {str(e)}")


@router.post("/connect-idp", response_model=IdpConnectionResponse)
async def connect_idp(
    request_data: IdpConnectionRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """
    Connect an identity provider (Google, Microsoft, Okta, Keycloak).
    """
    try:
        progress_id = _resolve_progress_key(customer_id, db)
        
        canonical_idp_type = _normalize_idp_type(request_data.idp_type)
        valid_idp_types = ["google_workspace", "microsoft_entra", "okta", "keycloak", "sentinelgrid"]
        if canonical_idp_type not in valid_idp_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid idp_type. Must be one of: {', '.join(valid_idp_types)}"
            )
        
        # Encrypt sensitive config data and store a vault reference in JSON
        encrypted_config = encrypt_secret(json.dumps(request_data.config))
        config_json = json.dumps({"secret_ref": encrypted_config})
        
        # Insert or update IdP config
        idp_config_id = str(uuid.uuid4())
        result = db.execute(
            text("""
                INSERT INTO customer_idp_config (
                    id, customer_id, idp_type, config_json, status, connected_at
                ) VALUES (
                    :id, :customer_id, :idp_type, CAST(:config_json AS jsonb), 'connected', NOW()
                )
                ON CONFLICT (customer_id, idp_type)
                DO UPDATE SET
                    config_json = EXCLUDED.config_json,
                    status = 'connected',
                    connected_at = NOW(),
                    updated_at = NOW()
                RETURNING id
            """),
            {
                "id": idp_config_id,
                "customer_id": customer_id,
                "idp_type": canonical_idp_type,
                "config_json": config_json
            }
        )
        row = result.fetchone()
        if row:
            idp_config_id = str(row[0])
        
        # Update onboarding progress
        db.execute(
            text("""
                INSERT INTO onboarding_progress (
                    customer_id,
                    step_idp_completed,
                    step_idp_completed_at,
                    services_selected
                )
                VALUES (
                    :customer_id,
                    true,
                    NOW(),
                    CAST(:services_selected AS jsonb)
                )
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    step_idp_completed = true,
                    step_idp_completed_at = NOW(),
                    services_selected = COALESCE(onboarding_progress.services_selected, '{}'::jsonb) || CAST(:services_selected AS jsonb),
                    updated_at = NOW()
            """),
            {
                "customer_id": progress_id,
                "services_selected": json.dumps({"idpProvider": canonical_idp_type}),
            },
        )
        db.commit()

        logger.info(f"IdP connected: {canonical_idp_type} for customer {customer_id}")

        return IdpConnectionResponse(
            success=True,
            idp_config_id=idp_config_id,
            status="connected",
            message=f"Successfully connected {canonical_idp_type}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting IdP: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to connect IdP: {str(e)}")


def _get_aws_external_id(customer_id: str, db) -> ExternalIdResponse:
    """Generate or retrieve external ID for AWS cross-account role assumption."""
    result = db.execute(
        text(
            """
            SELECT external_id
            FROM customer_cloud_accounts
            WHERE customer_id = :customer_id
              AND cloud_provider = 'aws'
            LIMIT 1
            """
        ),
        {"customer_id": customer_id},
    ).fetchone()

    if result and result[0]:
        external_id = result[0]
    else:
        external_id = str(uuid.uuid4())

    sentinelgrid_account_id = "987654321098"  # TODO: Move to config
    return ExternalIdResponse(
        external_id=external_id,
        sentinelgrid_account_id=sentinelgrid_account_id,
    )


@router.get("/aws/external-id", response_model=ExternalIdResponse)
async def get_aws_external_id(
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """
    Generate or retrieve external ID for AWS cross-account role assumption.
    """
    try:
        return _get_aws_external_id(customer_id, db)
    except Exception as e:
        logger.error(f"Error generating external ID: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate external ID: {str(e)}")


def _artifact_response(customer_id: str, db):
    tenant_row = db.execute(
        text(
            """
            SELECT t.slug
            FROM tenants t
            JOIN organizations o ON o.id = t.organization_id
            JOIN customers c ON c.id = o.customer_id
            WHERE c.id = :cid
            ORDER BY t.created_at ASC
            LIMIT 1
            """
        ),
        {"cid": customer_id},
    ).first()
    tenant_slug = tenant_row[0] if tenant_row else "tenant"
    namespace = _tenant_namespace_from_slug(tenant_slug)
    ecr_repo, helm_repo, s3_prefix = _artifact_endpoints(namespace)
    return ArtifactAccessResponse(
        tenant_namespace=namespace,
        ecr_repo=ecr_repo,
        helm_repo=helm_repo,
        s3_prefix=s3_prefix,
        notes="Ensure ECR/S3/IAM are provisioned per tenant; these values are derived from settings.",
    )


@router.get("/artifacts", response_model=ArtifactAccessResponse)
async def get_artifact_access(
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session),
):
    """Return tenant-scoped artifact endpoints (ECR/Helm/S3 prefixes)."""
    try:
        return _artifact_response(customer_id, db)
    except Exception as e:
        logger.error(f"Failed to fetch artifact access info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch artifact access info")


@portal_router.get("/artifacts", response_model=ArtifactAccessResponse)
async def get_artifact_access_portal(
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session),
):
    """Tenant-scoped artifact endpoints exposed under /api/iam-portal/onboarding for the UI."""
    try:
        return _artifact_response(customer_id, db)
    except Exception as e:
        logger.error(f"Failed to fetch artifact access info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch artifact access info")


@router.get("/cloud/providers")
async def list_cloud_provider_registry(
    customer_id: str = Depends(get_onboarding_customer_id),
):
    """Return registry-driven cloud provider metadata for onboarding."""
    try:
        payload = provider_registry_payload()
        payload["tenant_id"] = customer_id
        return payload
    except Exception as exc:
        logger.error("Failed to load cloud provider registry: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Cloud provider registry unavailable")


@router.post("/connect-cloud", response_model=CloudConnectionResponse)
async def connect_cloud(
    request_data: CloudConnectionRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """Connect a cloud provider through the registry-driven onboarding path."""
    normalized = _normalize_cloud_connection_request(request_data)
    provider = normalized.cloud_provider
    adapter_backed = provider_has_adapter(provider)
    if not _cloud_provider_has_runtime_connector(provider):
        raise HTTPException(
            status_code=501,
            detail=f"Cloud provider '{request_data.cloud_provider}' is configured but no connector adapter is available yet",
        )

    if provider == "aws":
        return await connect_aws(normalized, request, customer_id, db)
    if provider == "azure":
        return await connect_azure(normalized, request, customer_id, db)
    if provider == "gcp":
        return await connect_gcp(normalized, request, customer_id, db)
    if adapter_backed:
        return await _connect_adapter_backed_cloud(normalized, request, customer_id, db)

    raise HTTPException(status_code=501, detail=f"Cloud provider '{provider}' is not supported")


@router.post("/connect-aws", response_model=CloudConnectionResponse)
async def connect_aws(
    request_data: CloudConnectionRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """
    Connect an AWS account.
    """
    try:
        if request_data.cloud_provider != "aws":
            raise HTTPException(status_code=400, detail="This endpoint is for AWS connections only")
        
        progress_id = _resolve_progress_key(customer_id, db)

        cfg = request_data.metadata or request_data.config or {}
        account_id = request_data.account_id or cfg.get("account_id")
        monitor_role_arn = request_data.monitor_role_arn or cfg.get("monitor_role_arn") or cfg.get("iam_role_arn") or cfg.get("role_arn")
        extra_log_groups = cfg.get("additional_log_group_arns") or []
        extra_s3_buckets = cfg.get("additional_s3_log_bucket_arns") or []
        org_mode = bool(cfg.get("org_mode"))
        regions = cfg.get("regions") or []
        create_flow_logs_log_group = bool(cfg.get("create_flow_logs_log_group") or cfg.get("create_flow_log_group"))
        create_db_audit_log_group = bool(cfg.get("create_db_audit_log_group") or cfg.get("create_db_audit_logs"))
        
        # Validate AWS Account ID format (12 digits)
        if not account_id or not str(account_id).isdigit() or len(str(account_id)) != 12:
            raise HTTPException(status_code=400, detail="AWS Account ID must be 12 digits")
        
        # Get or generate external ID
        external_id_result = _get_aws_external_id(customer_id, db)
        external_id = external_id_result.external_id
        
        # Test connection (if role ARN provided)
        test_result = None
        log_health = None
        if monitor_role_arn:
            # Validate ARN format
            from app.services.aws_connection_tester import AWSConnectionTester
            tester = AWSConnectionTester()
            
            if not tester.validate_role_arn(monitor_role_arn):
                raise HTTPException(status_code=400, detail="Invalid IAM Role ARN format")
            
            # Perform actual role assumption test
            try:
                test_result = tester.test_role_assumption(
                    role_arn=monitor_role_arn,
                    external_id=external_id
                )
                # Optional: check access to provided log groups/buckets
                if extra_log_groups or extra_s3_buckets:
                    log_health = tester.test_log_access(
                        role_arn=monitor_role_arn,
                        external_id=external_id,
                        log_groups=extra_log_groups,
                        s3_buckets=extra_s3_buckets
                    )
                
                if not test_result.get("success"):
                    # Connection test failed - still allow saving, but warn user
                    logger.warning(f"AWS connection test failed for account {request_data.account_id}: {test_result.get('message')}")
                    # Don't raise exception - allow user to save and fix later
            except Exception as e:
                logger.error(f"Error testing AWS connection: {e}", exc_info=True)
                # Don't fail the request - allow saving with warning
                test_result = {
                    "success": False,
                    "message": f"Connection test encountered an error: {str(e)}",
                    "error": str(e)
                }
        
        # Encrypt service principal secret if provided
        encrypted_secret = None
        if request_data.service_principal_secret:
            encrypted_secret = encrypt_secret(request_data.service_principal_secret)
        
        # Insert or update cloud account
        cloud_account_id = str(uuid.uuid4())
        merged_metadata = {
            "org_mode": org_mode,
            "regions": regions,
            "additional_log_group_arns": extra_log_groups,
            "additional_s3_log_bucket_arns": extra_s3_buckets,
            "create_flow_logs_log_group": create_flow_logs_log_group,
            "create_db_audit_log_group": create_db_audit_log_group,
        }
        if request_data.metadata:
            merged_metadata["metadata"] = request_data.metadata
        if log_health:
            merged_metadata["health"] = log_health
        result = db.execute(
            text("""
                INSERT INTO customer_cloud_accounts (
                    id, customer_id, cloud_provider, account_id, account_name,
                    integration_method, monitor_role_arn, external_id,
                    service_principal_secret_encrypted, status, connected_at, metadata
                ) VALUES (
                    :id, :customer_id, :cloud_provider, :account_id, :account_name,
                    :integration_method, :monitor_role_arn, :external_id,
                    :service_principal_secret_encrypted, 'connected', NOW(), CAST(:metadata AS jsonb)
                )
                ON CONFLICT (customer_id, cloud_provider, account_id)
                DO UPDATE SET
                    account_name = EXCLUDED.account_name,
                    integration_method = EXCLUDED.integration_method,
                    monitor_role_arn = EXCLUDED.monitor_role_arn,
                    external_id = EXCLUDED.external_id,
                    service_principal_secret_encrypted = EXCLUDED.service_principal_secret_encrypted,
                    status = 'connected',
                    connected_at = NOW(),
                    updated_at = NOW(),
                    metadata = EXCLUDED.metadata
                RETURNING id
            """),
            {
                "id": cloud_account_id,
                "customer_id": customer_id,
                "cloud_provider": request_data.cloud_provider,
                "account_id": account_id,
                "account_name": request_data.account_name,
                "integration_method": request_data.integration_method,
                "monitor_role_arn": monitor_role_arn,
                "external_id": external_id,
                "service_principal_secret_encrypted": encrypted_secret,
                "metadata": json.dumps(merged_metadata)
            }
        )
        row = result.fetchone()
        if row:
            cloud_account_id = str(row[0])
        
        # Update onboarding progress
        db.execute(
            text("""
                INSERT INTO onboarding_progress (customer_id, step_cloud_completed, step_cloud_completed_at)
                VALUES (:customer_id, true, NOW())
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    step_cloud_completed = true,
                    step_cloud_completed_at = NOW(),
                    updated_at = NOW()
            """),
            {"customer_id": progress_id}
        )
        db.commit()
        
        logger.info(f"AWS account connected: {request_data.account_id} for customer {customer_id}")
        
        return CloudConnectionResponse(
            success=True,
            cloud_account_id=cloud_account_id,
            status="connected",
            message="AWS account connected successfully",
            test_connection_result=test_result,
            health=log_health
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting AWS account: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to connect AWS account: {str(e)}")


@router.post("/connect-azure", response_model=CloudConnectionResponse)
async def connect_azure(
    request_data: CloudConnectionRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """
    Connect an Azure subscription.
    """
    try:
        if request_data.cloud_provider != "azure":
            raise HTTPException(status_code=400, detail="This endpoint is for Azure connections only")
        
        progress_id = _resolve_progress_key(customer_id, db)
        
        # Validate subscription ID format (UUID)
        from app.services.azure_connection_tester import AzureConnectionTester
        tester = AzureConnectionTester()
        
        if not tester.validate_subscription_id(request_data.account_id):
            raise HTTPException(
                status_code=400,
                detail="Azure Subscription ID must be a valid UUID format"
            )
        
        # Validate service principal credentials
        if not request_data.service_principal_id:
            raise HTTPException(
                status_code=400,
                detail="Service Principal ID (Client ID) is required for Azure"
            )
        
        if not request_data.service_principal_secret:
            raise HTTPException(
                status_code=400,
                detail="Client Secret is required for Azure"
            )
        
        # Extract tenant ID from metadata or request
        tenant_id = None
        if request_data.metadata and "tenant_id" in request_data.metadata:
            tenant_id = request_data.metadata["tenant_id"]
        else:
            raise HTTPException(
                status_code=400,
                detail="Tenant ID is required. Please provide it in the metadata field."
            )
        
        # Validate tenant ID format
        if not tester.validate_tenant_id(tenant_id):
            raise HTTPException(
                status_code=400,
                detail="Tenant ID must be a valid UUID format"
            )
        
        # Validate client ID format
        if not tester.validate_client_id(request_data.service_principal_id):
            raise HTTPException(
                status_code=400,
                detail="Client ID must be a valid UUID format"
            )
        
        # Test connection
        test_result = None
        try:
            test_result = tester.test_service_principal(
                tenant_id=tenant_id,
                client_id=request_data.service_principal_id,
                client_secret=request_data.service_principal_secret,
                subscription_id=request_data.account_id
            )
            
            if not test_result.get("success"):
                logger.warning(f"Azure connection test failed for subscription {request_data.account_id}: {test_result.get('message')}")
                # Don't raise exception - allow user to save and fix later
        except Exception as e:
            logger.error(f"Error testing Azure connection: {e}", exc_info=True)
            test_result = {
                "success": False,
                "message": f"Connection test encountered an error: {str(e)}",
                "error": str(e)
            }
        
        # Encrypt client secret
        encrypted_secret = encrypt_secret(request_data.service_principal_secret)
        
        # Store tenant_id in metadata if not already there
        metadata = request_data.metadata or {}
        metadata["tenant_id"] = tenant_id
        
        # Insert or update cloud account
        cloud_account_id = str(uuid.uuid4())
        result = db.execute(
            text("""
                INSERT INTO customer_cloud_accounts (
                    id, customer_id, cloud_provider, account_id, account_name,
                    integration_method, service_principal_id,
                    service_principal_secret_encrypted, status, connected_at, metadata
                ) VALUES (
                    :id, :customer_id, :cloud_provider, :account_id, :account_name,
                    :integration_method, :service_principal_id,
                    :service_principal_secret_encrypted, 'connected', NOW(), CAST(:metadata AS jsonb)
                )
                ON CONFLICT (customer_id, cloud_provider, account_id)
                DO UPDATE SET
                    account_name = EXCLUDED.account_name,
                    integration_method = EXCLUDED.integration_method,
                    service_principal_id = EXCLUDED.service_principal_id,
                    service_principal_secret_encrypted = EXCLUDED.service_principal_secret_encrypted,
                    status = 'connected',
                    connected_at = NOW(),
                    updated_at = NOW(),
                    metadata = EXCLUDED.metadata
                RETURNING id
            """),
            {
                "id": cloud_account_id,
                "customer_id": customer_id,
                "cloud_provider": request_data.cloud_provider,
                "account_id": request_data.account_id,
                "account_name": request_data.account_name,
                "integration_method": request_data.integration_method,
                "service_principal_id": request_data.service_principal_id,
                "service_principal_secret_encrypted": encrypted_secret,
                "metadata": json.dumps(metadata)
            }
        )
        row = result.fetchone()
        if row:
            cloud_account_id = str(row[0])
        
        # Update onboarding progress
        db.execute(
            text("""
                INSERT INTO onboarding_progress (customer_id, step_cloud_completed, step_cloud_completed_at)
                VALUES (:customer_id, true, NOW())
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    step_cloud_completed = true,
                    step_cloud_completed_at = NOW(),
                    updated_at = NOW()
            """),
            {"customer_id": progress_id}
        )
        db.commit()
        
        logger.info(f"Azure subscription connected: {request_data.account_id} for customer {customer_id}")
        
        return CloudConnectionResponse(
            success=True,
            cloud_account_id=cloud_account_id,
            status="connected",
            message="Azure subscription connected successfully",
            test_connection_result=test_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting Azure subscription: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to connect Azure subscription: {str(e)}")


@router.post("/connect-gcp", response_model=CloudConnectionResponse)
async def connect_gcp(
    request_data: CloudConnectionRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """
    Connect a GCP project.
    """
    try:
        if request_data.cloud_provider != "gcp":
            raise HTTPException(status_code=400, detail="This endpoint is for GCP connections only")
        
        progress_id = _resolve_progress_key(customer_id, db)
        
        # Validate project ID format
        from app.services.gcp_connection_tester import GCPConnectionTester
        tester = GCPConnectionTester()
        
        if not tester.validate_project_id(request_data.account_id):
            raise HTTPException(
                status_code=400,
                detail="GCP Project ID must be 6-30 characters, start with lowercase letter, and contain only lowercase letters, numbers, and hyphens"
            )
        
        # Validate service account credentials
        if not request_data.service_principal_id:
            raise HTTPException(
                status_code=400,
                detail="Service Account Email is required for GCP"
            )
        
        if not request_data.service_principal_secret:
            raise HTTPException(
                status_code=400,
                detail="Service Account JSON Key is required for GCP"
            )
        
        # Validate service account email format
        if not tester.validate_service_account_email(request_data.service_principal_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid service account email format. Expected format: sa-id@project-id.iam.gserviceaccount.com"
            )
        
        # Test connection
        test_result = None
        try:
            test_result = tester.test_service_account(
                project_id=request_data.account_id,
                service_account_key_json=request_data.service_principal_secret
            )
            
            if not test_result.get("success"):
                logger.warning(f"GCP connection test failed for project {request_data.account_id}: {test_result.get('message')}")
                # Don't raise exception - allow user to save and fix later
        except Exception as e:
            logger.error(f"Error testing GCP connection: {e}", exc_info=True)
            test_result = {
                "success": False,
                "message": f"Connection test encountered an error: {str(e)}",
                "error": str(e)
            }
        
        # Encrypt service account key JSON
        encrypted_secret = encrypt_secret(request_data.service_principal_secret)
        
        # Store service account email and project ID in metadata
        metadata = request_data.metadata or {}
        metadata["service_account_email"] = request_data.service_principal_id
        metadata["project_id"] = request_data.account_id
        
        # Insert or update cloud account
        cloud_account_id = str(uuid.uuid4())
        result = db.execute(
            text("""
                INSERT INTO customer_cloud_accounts (
                    id, customer_id, cloud_provider, account_id, account_name,
                    integration_method, service_principal_id,
                    service_principal_secret_encrypted, status, connected_at, metadata
                ) VALUES (
                    :id, :customer_id, :cloud_provider, :account_id, :account_name,
                    :integration_method, :service_principal_id,
                    :service_principal_secret_encrypted, 'connected', NOW(), CAST(:metadata AS jsonb)
                )
                ON CONFLICT (customer_id, cloud_provider, account_id)
                DO UPDATE SET
                    account_name = EXCLUDED.account_name,
                    integration_method = EXCLUDED.integration_method,
                    service_principal_id = EXCLUDED.service_principal_id,
                    service_principal_secret_encrypted = EXCLUDED.service_principal_secret_encrypted,
                    status = 'connected',
                    connected_at = NOW(),
                    updated_at = NOW(),
                    metadata = EXCLUDED.metadata
                RETURNING id
            """),
            {
                "id": cloud_account_id,
                "customer_id": customer_id,
                "cloud_provider": request_data.cloud_provider,
                "account_id": request_data.account_id,
                "account_name": request_data.account_name,
                "integration_method": request_data.integration_method,
                "service_principal_id": request_data.service_principal_id,
                "service_principal_secret_encrypted": encrypted_secret,
                "metadata": json.dumps(metadata)
            }
        )
        row = result.fetchone()
        if row:
            cloud_account_id = str(row[0])
        
        # Update onboarding progress
        db.execute(
            text("""
                INSERT INTO onboarding_progress (customer_id, step_cloud_completed, step_cloud_completed_at)
                VALUES (:customer_id, true, NOW())
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    step_cloud_completed = true,
                    step_cloud_completed_at = NOW(),
                    updated_at = NOW()
            """),
            {"customer_id": progress_id}
        )
        db.commit()
        
        logger.info(f"GCP project connected: {request_data.account_id} for customer {customer_id}")
        
        return CloudConnectionResponse(
            success=True,
            cloud_account_id=cloud_account_id,
            status="connected",
            message="GCP project connected successfully",
            test_connection_result=test_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting GCP project: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to connect GCP project: {str(e)}")


async def _connect_adapter_backed_cloud(
    request_data: CloudConnectionRequest,
    request: Request,
    customer_id: str,
    db,
):
    """Connect a provider target through the shared adapter-backed onboarding path."""
    try:
        from sg_core.cloud.onboarding import CloudConnectionValidationError, validate_cloud_connection

        provider = request_data.cloud_provider
        progress_id = _resolve_progress_key(customer_id, db)
        cfg = request_data.metadata or request_data.config or {}
        try:
            connection = validate_cloud_connection(
                provider,
                config=cfg,
                account_id=request_data.account_id,
                account_name=request_data.account_name,
                secret=request_data.service_principal_secret,
            )
        except CloudConnectionValidationError as exc:
            raise HTTPException(status_code=400, detail=exc.detail) from exc

        encrypted_secret = encrypt_secret(connection.secret, tenant_id=customer_id)

        cloud_account_id = str(uuid.uuid4())
        result = db.execute(
            text("""
                INSERT INTO customer_cloud_accounts (
                    id, customer_id, cloud_provider, account_id, account_name,
                    integration_method, service_principal_id,
                    service_principal_secret_encrypted, status, connected_at, metadata
                ) VALUES (
                    :id, :customer_id, :cloud_provider, :account_id, :account_name,
                    :integration_method, :service_principal_id,
                    :service_principal_secret_encrypted, 'connected', NOW(), CAST(:metadata AS jsonb)
                )
                ON CONFLICT (customer_id, cloud_provider, account_id)
                DO UPDATE SET
                    account_name = EXCLUDED.account_name,
                    integration_method = EXCLUDED.integration_method,
                    service_principal_id = EXCLUDED.service_principal_id,
                    service_principal_secret_encrypted = EXCLUDED.service_principal_secret_encrypted,
                    status = 'connected',
                    connected_at = NOW(),
                    updated_at = NOW(),
                    metadata = EXCLUDED.metadata
                RETURNING id
            """),
            {
                "id": cloud_account_id,
                "customer_id": customer_id,
                "cloud_provider": connection.provider,
                "account_id": connection.account_id,
                "account_name": connection.account_name,
                "integration_method": request_data.integration_method or "manual",
                "service_principal_id": connection.service_principal_id,
                "service_principal_secret_encrypted": encrypted_secret,
                "metadata": json.dumps(connection.metadata),
            }
        )
        row = result.fetchone()
        if row:
            cloud_account_id = str(row[0])

        db.execute(
            text("""
                INSERT INTO onboarding_progress (customer_id, step_cloud_completed, step_cloud_completed_at)
                VALUES (:customer_id, true, NOW())
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    step_cloud_completed = true,
                    step_cloud_completed_at = NOW(),
                    updated_at = NOW()
            """),
            {"customer_id": progress_id}
        )
        db.commit()

        logger.info(
            "%s adapter-backed cloud target connected: %s for customer %s",
            connection.provider,
            connection.account_id,
            customer_id,
        )
        return CloudConnectionResponse(
            success=True,
            cloud_account_id=cloud_account_id,
            status="connected",
            message=f"{connection.provider} target connected successfully",
            test_connection_result=connection.health,
            health=connection.health,
        )

    except HTTPException:
        raise
    except Exception as e:
        provider = getattr(request_data, "cloud_provider", "cloud")
        logger.error("Error connecting %s adapter-backed cloud target: %s", provider, e, exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to connect {provider} target: {str(e)}")


def _resolve_change_request_provider(
    change_request_id: str,
    customer_id: str,
    requested_provider: Optional[str],
    db,
) -> str:
    row = db.execute(
        text("""
            SELECT provider
            FROM infrastructure_change_requests
            WHERE id = :id AND tenant_id = :tenant_id
            LIMIT 1
        """),
        {"id": change_request_id, "tenant_id": customer_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Infrastructure change request not found")

    raw_provider = str(row["provider"] or "").strip().lower()
    if not raw_provider:
        raise HTTPException(status_code=409, detail="Infrastructure change request is missing a provider")
    provider = _canonical_cloud_provider(raw_provider)

    if requested_provider:
        requested = _canonical_cloud_provider(requested_provider)
        if requested != provider:
            raise HTTPException(
                status_code=409,
                detail=f"Change request provider mismatch: expected {provider}, got {requested}",
            )
    return provider


def _assert_expected_change_provider(
    provider: str,
    expected_provider: Optional[str],
) -> None:
    if expected_provider and provider != _canonical_cloud_provider(expected_provider):
        raise HTTPException(
            status_code=409,
            detail=f"{expected_provider} route can only operate on {expected_provider} change requests",
        )


def _cloud_change_http_error(exc: CloudChangeRequestError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _failed_change_result(detail: Any) -> Dict[str, Any]:
    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("error") or str(detail)
        return {"success": False, "error": message, "detail": detail}
    return {"success": False, "error": str(detail)}


def _mark_change_request_failed(
    change_request_id: str,
    customer_id: str,
    detail: Any,
    db,
) -> None:
    db.execute(
        text("""
            UPDATE infrastructure_change_requests
            SET status = 'failed',
                apply_result = CAST(:apply_result AS jsonb),
                updated_at = NOW()
            WHERE id = :id AND tenant_id = :tenant_id
        """),
        {
            "id": change_request_id,
            "tenant_id": customer_id,
            "apply_result": json.dumps(_failed_change_result(detail)),
        },
    )
    db.commit()


def _approve_cloud_change_request(
    change_request_id: str,
    request_data: InfrastructureChangeApprovalRequest,
    customer_id: str,
    request_context: RequestContext,
    db,
    expected_provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Approve a provider-backed infrastructure change request."""
    provider = _resolve_change_request_provider(change_request_id, customer_id, request_data.provider, db)
    _assert_expected_change_provider(provider, expected_provider)
    try:
        row = db.execute(
            text("""
                SELECT id, tenant_id, cloud_account_id, provider, status, server_id, firewall_id,
                       scope_hash, pre_state, proposed_diff
                FROM infrastructure_change_requests
                WHERE id = :id AND tenant_id = :tenant_id AND provider = :provider
                LIMIT 1
            """),
            {"id": change_request_id, "tenant_id": customer_id, "provider": provider},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Infrastructure change request not found")
        if row["status"] in {"applied", "applying"}:
            raise HTTPException(status_code=409, detail=f"Change request is already {row['status']}")

        approval = prepare_cloud_change_approval(
            provider,
            pre_state=row["pre_state"] or {},
            proposed_diff=row["proposed_diff"] or {},
            inputs=change_request_approval_inputs(request_data),
        )

        approver = request_context.user_id or "internal_service"
        db.execute(
            text("""
                UPDATE infrastructure_change_requests
                SET status = 'approved',
                    proposed_diff = CAST(:proposed_diff AS jsonb),
                    approved_by = :approved_by,
                    approved_at = NOW(),
                    approval_notes = :approval_notes,
                    updated_at = NOW()
                WHERE id = :id AND tenant_id = :tenant_id
            """),
            {
                "id": change_request_id,
                "tenant_id": customer_id,
                "proposed_diff": json.dumps(approval.proposed_diff),
                "approved_by": approver,
                "approval_notes": getattr(request_data, "notes", None),
            },
        )
        db.commit()
        return {
            "success": True,
            "provider": provider,
            "change_request_id": change_request_id,
            "status": "approved",
            "approved_by": approver,
            "proposed_diff": approval.proposed_diff,
        }
    except CloudChangeRequestError as exc:
        raise _cloud_change_http_error(exc) from exc
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error approving cloud change request: %s", e, exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to approve cloud change request: {str(e)}")


def _apply_cloud_change_request(
    change_request_id: str,
    request_data: InfrastructureChangeApplyRequest,
    customer_id: str,
    request_context: RequestContext,
    db,
    expected_provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply an approved provider-backed infrastructure change request."""
    provider = _resolve_change_request_provider(change_request_id, customer_id, request_data.provider, db)
    _assert_expected_change_provider(provider, expected_provider)
    if not getattr(request_data, "confirm", True):
        raise HTTPException(status_code=400, detail="Apply confirmation is required")

    row = db.execute(
        text("""
            SELECT icr.id, icr.cloud_account_id, icr.status, icr.server_id, icr.firewall_id,
                   icr.scope_hash, icr.pre_state, icr.proposed_diff,
                   cca.account_id, cca.account_name, cca.service_principal_secret_encrypted, cca.metadata
            FROM infrastructure_change_requests icr
            JOIN customer_cloud_accounts cca ON cca.id = icr.cloud_account_id
            WHERE icr.id = :id
              AND icr.tenant_id = :tenant_id
              AND icr.provider = :provider
              AND cca.customer_id = :tenant_id
              AND cca.cloud_provider = :provider
            LIMIT 1
        """),
        {"id": change_request_id, "tenant_id": customer_id, "provider": provider},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Infrastructure change request not found")
    if row["status"] != "approved":
        raise HTTPException(status_code=409, detail="Infrastructure change request must be approved before apply")

    if not row["service_principal_secret_encrypted"]:
        raise HTTPException(status_code=400, detail=f"Missing {provider} credential reference")

    apply_user = request_context.user_id or "internal_service"
    try:
        token = decrypt_secret(row["service_principal_secret_encrypted"])
        metadata = row["metadata"] or {}
        prepared = prepare_cloud_change_apply(
            provider,
            account_id=str(row["account_id"]) if row["account_id"] is not None else None,
            account_name=row["account_name"],
            secret=token,
            metadata=metadata,
            change_request=row,
        )
    except CloudChangeRequestError as exc:
        raise _cloud_change_http_error(exc) from exc
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error preparing cloud change request apply: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to prepare cloud change request apply: {str(e)}")

    try:
        db.execute(
            text("""
                UPDATE infrastructure_change_requests
                SET status = 'applying',
                    apply_requested_by = :apply_requested_by,
                    apply_started_at = NOW(),
                    updated_at = NOW()
                WHERE id = :id AND tenant_id = :tenant_id
            """),
            {"id": change_request_id, "tenant_id": customer_id, "apply_requested_by": apply_user},
        )
        db.commit()

        apply_result = apply_prepared_cloud_change(prepared)
        db.execute(
            text("""
                UPDATE infrastructure_change_requests
                SET status = 'applied',
                    apply_completed_at = NOW(),
                    apply_result = CAST(:apply_result AS jsonb),
                    updated_at = NOW()
                WHERE id = :id AND tenant_id = :tenant_id
            """),
            {
                "id": change_request_id,
                "tenant_id": customer_id,
                "apply_result": json.dumps(apply_result.result_payload),
            },
        )
        db.execute(
            text("""
                UPDATE customer_cloud_accounts
                SET metadata = CAST(:metadata AS jsonb),
                    updated_at = NOW()
                WHERE id = :cloud_account_id AND customer_id = :tenant_id
            """),
            {
                "cloud_account_id": str(row["cloud_account_id"]),
                "tenant_id": customer_id,
                "metadata": json.dumps(apply_result.account_metadata),
            },
        )
        db.commit()
        return {
            "success": True,
            "change_request_id": change_request_id,
            "status": "applied",
            "apply_result": apply_result.result_payload,
        }
    except CloudChangeRequestError as exc:
        db.rollback()
        _mark_change_request_failed(change_request_id, customer_id, exc.detail, db)
        raise _cloud_change_http_error(exc) from exc
    except Exception as e:
        db.rollback()
        try:
            _mark_change_request_failed(change_request_id, customer_id, str(e), db)
        except Exception:
            db.rollback()
        logger.error("Error applying cloud change request: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to apply cloud change request: {str(e)}")


@router.post("/cloud/change-requests/{change_request_id}/approve")
async def approve_infrastructure_change_request(
    change_request_id: str,
    request_data: InfrastructureChangeApprovalRequest,
    customer_id: str = Depends(get_onboarding_customer_id),
    request_context: RequestContext = Depends(get_current_request_context),
    db = Depends(get_tenant_session),
):
    """Approve a provider-backed infrastructure change request."""
    return _approve_cloud_change_request(change_request_id, request_data, customer_id, request_context, db)


@router.post("/cloud/change-requests/{change_request_id}/apply")
async def apply_infrastructure_change_request(
    change_request_id: str,
    request_data: InfrastructureChangeApplyRequest,
    customer_id: str = Depends(get_onboarding_customer_id),
    request_context: RequestContext = Depends(get_current_request_context),
    db = Depends(get_tenant_session),
):
    """Apply an approved provider-backed infrastructure change request."""
    return _apply_cloud_change_request(change_request_id, request_data, customer_id, request_context, db)


@router.post("/register-agent", response_model=EndpointAgentRegistrationResponse)
async def register_endpoint_agent(
    request_data: EndpointAgentRegistrationRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """
    Register an endpoint protection agent.
    """
    try:
        progress_id = _resolve_progress_key(customer_id, db)
        
        # Insert or update agent registration
        db.execute(
            text("""
                INSERT INTO customer_endpoint_agents (
                    customer_id, agent_id, agent_type, hostname, ip_address,
                    os_type, os_version, os_arch, agent_version, status,
                    registered_at, last_seen_at, metadata
                ) VALUES (
                    :customer_id, :agent_id, :agent_type, :hostname, :ip_address::inet,
                    :os_type, :os_version, :os_arch, :agent_version, 'active',
                    NOW(), NOW(), CAST(:metadata AS jsonb)
                )
                ON CONFLICT (customer_id, agent_id)
                DO UPDATE SET
                    hostname = EXCLUDED.hostname,
                    ip_address = EXCLUDED.ip_address,
                    os_type = EXCLUDED.os_type,
                    os_version = EXCLUDED.os_version,
                    os_arch = EXCLUDED.os_arch,
                    agent_version = EXCLUDED.agent_version,
                    status = 'active',
                    last_seen_at = NOW(),
                    updated_at = NOW(),
                    metadata = EXCLUDED.metadata
            """),
            {
                "customer_id": customer_id,
                "agent_id": request_data.agent_id,
                "agent_type": request_data.agent_type,
                "hostname": request_data.hostname,
                "ip_address": request_data.ip_address,
                "os_type": request_data.os_type,
                "os_version": request_data.os_version,
                "os_arch": request_data.os_arch,
                "agent_version": request_data.agent_version,
                "metadata": json.dumps(request_data.metadata or {})
            }
        )
        
        # Update onboarding progress
        db.execute(
            text("""
                INSERT INTO onboarding_progress (customer_id, step_endpoint_completed, step_endpoint_completed_at)
                VALUES (:customer_id, true, NOW())
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    step_endpoint_completed = true,
                    step_endpoint_completed_at = NOW(),
                    updated_at = NOW()
            """),
            {"customer_id": progress_id}
        )
        db.commit()
        
        logger.info(f"Agent registered: {request_data.agent_id} for customer {customer_id}")
        
        return EndpointAgentRegistrationResponse(
            success=True,
            agent_id=request_data.agent_id,
            status="active",
            message="Agent registered successfully"
        )
        
    except Exception as e:
        logger.error(f"Error registering agent: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to register agent: {str(e)}")


# ============================================================================
# AppSec / AI Shield / Ticketing connection handlers
# ============================================================================

@router.post("/connect-appsec")
async def connect_appsec(
    request_data: AppSecConnectionRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """Connect Application Security and only mark the step complete when health is healthy."""
    try:
        progress_id = _resolve_progress_key(customer_id, db)
        health = _probe_appsec(request_data.dict())
        status = health.get("status") or "unknown"
        success = status == "healthy"
        message = (
            "AppSec connected"
            if success
            else f"AppSec settings were saved, but health is {status}"
        )
        db.execute(
            text("""
                INSERT INTO onboarding_progress (customer_id, step_appsec_completed, services_selected, appsec_health, appsec_config, updated_at)
                VALUES (:customer_id, :step_appsec_completed, jsonb_set('{}'::jsonb, '{appsec}', 'true'::jsonb, true), CAST(:health AS jsonb), CAST(:config AS jsonb), NOW())
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    step_appsec_completed = :step_appsec_completed,
                    services_selected = jsonb_set(COALESCE(onboarding_progress.services_selected, '{}'::jsonb), '{appsec}', 'true'::jsonb, true),
                    appsec_health = CAST(:health AS jsonb),
                    appsec_config = CAST(:config AS jsonb),
                    updated_at = NOW()
            """),
            {
                "customer_id": progress_id,
                "step_appsec_completed": success,
                "health": json.dumps(health),
                "config": json.dumps(request_data.dict()),
            }
        )
        db.commit()
        return {"success": success, "status": status, "message": message, "health": health}
    except Exception as e:
        logger.error(f"Error connecting AppSec: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to connect AppSec: {str(e)}")


@router.post("/connect-ai")
async def connect_ai(
    request_data: AIShieldConnectionRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """Connect AI Shield and only mark the step complete when the saved endpoint is healthy."""
    try:
        progress_id = _resolve_progress_key(customer_id, db)
        health = _probe_ai(request_data.dict())
        status = health.get("status") or "unknown"
        success = status == "healthy"
        message = (
            "AI Shield connected"
            if success
            else f"AI Shield configuration saved, but health is {status}"
        )
        db.execute(
            text("""
                INSERT INTO onboarding_progress (customer_id, step_ai_completed, services_selected, ai_health, ai_config, updated_at)
                VALUES (:customer_id, :step_ai_completed, jsonb_set('{}'::jsonb, '{aiShield}', to_jsonb(CAST(:mode AS text)), true), CAST(:health AS jsonb), CAST(:config AS jsonb), NOW())
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    step_ai_completed = :step_ai_completed,
                    services_selected = jsonb_set(COALESCE(onboarding_progress.services_selected, '{}'::jsonb), '{aiShield}', to_jsonb(CAST(:mode AS text)), true),
                    ai_health = CAST(:health AS jsonb),
                    ai_config = CAST(:config AS jsonb),
                    updated_at = NOW()
            """),
            {
                "customer_id": progress_id,
                "step_ai_completed": success,
                "mode": request_data.mode,
                "health": json.dumps(health),
                "config": json.dumps(request_data.dict()),
            }
        )
        db.commit()
        return {"success": success, "status": status, "message": message, "health": health}
    except Exception as e:
        logger.error(f"Error connecting AI Shield: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to connect AI Shield: {str(e)}")


@router.post("/connect-ticketing")
async def connect_ticketing(
    request_data: TicketingConnectionRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """Connect ticketing and only mark the step complete when the handoff validates as healthy."""
    try:
        progress_id = _resolve_progress_key(customer_id, db)
        valid_providers = {"internal", "jira", "servicenow"}
        valid_assignment_modes = {"project_default", "service_owner", "named_owner"}
        valid_assignee_identifier_types = {"account_id", "email", "username", "sys_id"}
        if request_data.provider not in valid_providers:
            raise HTTPException(status_code=400, detail="Invalid ticketing provider")
        assignment_mode = request_data.assignment_mode or "service_owner"
        if assignment_mode not in valid_assignment_modes:
            raise HTTPException(status_code=400, detail="Invalid ticket routing mode")
        assignee_identifier_type = request_data.assignee_identifier_type or _default_assignee_identifier_type(request_data.provider)
        if assignee_identifier_type not in valid_assignee_identifier_types:
            raise HTTPException(status_code=400, detail="Invalid assignee identifier type")
        if request_data.provider != "internal":
            if not request_data.url:
                raise HTTPException(status_code=400, detail="Ticketing URL is required")
            if not request_data.project:
                raise HTTPException(status_code=400, detail="Project or assignment group is required")
            if not request_data.api_key:
                raise HTTPException(status_code=400, detail="API token is required")
        if assignment_mode == "named_owner" and not request_data.default_assignee:
            raise HTTPException(status_code=400, detail="Default assignee is required for named owner routing")
        if request_data.provider == "servicenow" and assignment_mode == "named_owner" and assignee_identifier_type not in {"username", "sys_id"}:
            raise HTTPException(status_code=400, detail="ServiceNow named owners must use username or sys_id")
        if request_data.notify_slack:
            if not request_data.slack_channel:
                raise HTTPException(status_code=400, detail="Slack channel is required when Slack notifications are enabled")
            if not request_data.slack_webhook_url:
                raise HTTPException(status_code=400, detail="Slack webhook URL is required when Slack notifications are enabled")

        soc_managed = True if request_data.soc_managed is None else bool(request_data.soc_managed)
        payload = request_data.dict(by_alias=False)
        payload["assignee_identifier_type"] = assignee_identifier_type
        health = _probe_ticketing(payload)
        db.execute(
            text("""
                INSERT INTO onboarding_progress (customer_id, step_ticketing_completed, services_selected, ticketing_health, ticketing_config, updated_at)
                VALUES (
                    :customer_id,
                    :step_ticketing_completed,
                    jsonb_set(
                        jsonb_set('{}'::jsonb, '{socManaged}', to_jsonb(:soc_managed), true),
                        '{ticketing}', to_jsonb(CAST(:provider AS text)), true
                    ),
                    CAST(:health AS jsonb),
                    CAST(:config AS jsonb),
                    NOW()
                )
                ON CONFLICT (customer_id)
                DO UPDATE SET
                    step_ticketing_completed = :step_ticketing_completed,
                    services_selected = jsonb_set(
                        jsonb_set(COALESCE(onboarding_progress.services_selected, '{}'::jsonb), '{socManaged}', to_jsonb(:soc_managed), true),
                        '{ticketing}', to_jsonb(CAST(:provider AS text)), true
                    ),
                    ticketing_health = CAST(:health AS jsonb),
                    ticketing_config = CAST(:config AS jsonb),
                    updated_at = NOW()
            """),
            {
                "customer_id": progress_id,
                "step_ticketing_completed": health.get("status") == "healthy",
                "provider": request_data.provider,
                "soc_managed": soc_managed,
                "health": json.dumps(health),
                "config": json.dumps(payload),
            }
        )
        db.commit()
        status = health.get("status") or "unknown"
        success = status == "healthy"
        message = (
            "Ticketing handoff is ready."
            if success
            else "Ticketing settings were saved, but the handoff still needs attention."
        )
        return {"success": success, "status": status, "message": message, "health": health}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting ticketing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to connect ticketing: {str(e)}")


@router.post("/ticketing-assignees/search", response_model=TicketingAssigneeLookupResponse)
async def search_ticketing_assignees(
    request_data: TicketingAssigneeLookupRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """Search Jira or ServiceNow assignees using draft or stored ticketing config."""
    try:
        progress_id = _resolve_progress_key(customer_id, db)
        stored_config = _load_ticketing_lookup_config(progress_id, db)
        lookup_config = _normalize_ticketing_lookup_config(stored_config, request_data)
        provider = str(lookup_config.get("provider") or "internal").lower()
        identifier_type = (
            lookup_config.get("assignee_identifier_type")
            or _default_assignee_identifier_type(provider)
        )
        source = "draft_config" if any(
            getattr(request_data, field, None)
            for field in ("provider", "url", "project", "api_key", "assignee_identifier_type")
        ) else "stored_config"

        results = await _lookup_ticketing_assignees(lookup_config)
        return {
            "provider": provider,
            "assigneeIdentifierType": identifier_type,
            "source": source,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching ticketing assignees: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search ticketing assignees: {str(e)}")


@router.post("/recheck-health")
async def recheck_health(
    request_data: RecheckHealthRequest,
    request: Request,
    customer_id: str = Depends(get_onboarding_customer_id),
    db = Depends(get_tenant_session)
):
    """Re-run health checks for appsec/ai/ticketing/cloud using stored config."""
    try:
        progress_id = _resolve_progress_key(customer_id, db)
        target = request_data.target
        if target not in ["appsec", "ai", "ticketing", "cloud", "git", "endpoint", "idp"]:
            raise HTTPException(status_code=400, detail="Invalid target")

        row = db.execute(
            text("""
                SELECT appsec_config, appsec_health, ai_config, ai_health, ticketing_config, ticketing_health,
                       step_endpoint_completed, step_idp_completed
                FROM onboarding_progress
                WHERE customer_id = :customer_id
            """),
            {"customer_id": progress_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Onboarding progress not found")

        update_sql = None
        health = {"status": "unknown", "checked_at": datetime.utcnow().isoformat() + "Z"}

        if target == "appsec":
            cfg = row[0] or {}
            health = _probe_appsec(cfg)
            update_sql = text("""
                UPDATE onboarding_progress
                SET appsec_health = :health::jsonb, updated_at = NOW()
                WHERE customer_id = :customer_id
            """)
        elif target == "ai":
            cfg = row[2] or {}
            health = _probe_ai(cfg)
            update_sql = text("""
                UPDATE onboarding_progress
                SET ai_health = :health::jsonb, updated_at = NOW()
                WHERE customer_id = :customer_id
            """)
        elif target == "ticketing":
            cfg = row[4] or {}
            health = _probe_ticketing(cfg)
            update_sql = text("""
                UPDATE onboarding_progress
                SET ticketing_health = :health::jsonb, updated_at = NOW()
                WHERE customer_id = :customer_id
            """)
        elif target == "idp":
            idp_provider = _load_latest_idp_provider(progress_id, db) or "sentinelgrid"
            health = _probe_idp({"idp_type": idp_provider})
            update_sql = text("""
                UPDATE onboarding_progress
                SET step_idp_completed = true,
                    step_idp_completed_at = COALESCE(step_idp_completed_at, NOW()),
                    updated_at = NOW()
                WHERE customer_id = :customer_id
            """)
        elif target == "endpoint":
            health = _get_endpoint_agent_health(progress_id, db)
            if (health.get("status") or "").lower() == "healthy":
                update_sql = text("""
                    UPDATE onboarding_progress
                    SET step_endpoint_completed = true,
                        step_endpoint_completed_at = COALESCE(step_endpoint_completed_at, NOW()),
                        updated_at = NOW()
                    WHERE customer_id = :customer_id
                """)
            else:
                update_sql = text("""
                    UPDATE onboarding_progress
                    SET step_endpoint_completed = false,
                        updated_at = NOW()
                    WHERE customer_id = :customer_id
                """)
        elif target == "git":
            # Lightweight placeholder: mark success if a provider exists
            prov = db.execute(
                text("""
                    SELECT id, metadata
                    FROM customer_git_providers
                    WHERE customer_id = :customer_id
                    ORDER BY connected_at DESC
                    LIMIT 1
                """),
                {"customer_id": customer_id}
            ).fetchone()
            if not prov:
                raise HTTPException(status_code=404, detail="No git provider found")
            prov_id = prov[0]
            health = {"success": True, "message": "Git health check placeholder"}
            db.execute(
                text("""
                    UPDATE customer_git_providers
                    SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{health}', :health::jsonb, true),
                        updated_at = NOW()
                    WHERE id = :prov_id
                """),
                {"prov_id": prov_id, "health": json.dumps(health)}
            )
            update_sql = None
        elif target == "cloud":
            acct_row = db.execute(
                text("""
                    SELECT cloud_provider, monitor_role_arn, external_id,
                           service_principal_secret_encrypted, metadata, account_id,
                           account_name
                    FROM customer_cloud_accounts
                    WHERE customer_id = :customer_id
                    ORDER BY connected_at DESC
                    LIMIT 1
                """),
                {"customer_id": customer_id}
            ).fetchone()
            if not acct_row:
                raise HTTPException(status_code=404, detail="No supported cloud account found")

            if len(acct_row) >= 6:
                cloud_provider = acct_row[0]
                monitor_role_arn = acct_row[1]
                external_id = acct_row[2]
                encrypted_secret = acct_row[3]
                metadata = acct_row[4] or {}
                account_id = acct_row[5]
                account_name = acct_row[6] if len(acct_row) >= 7 else None
            else:
                # Older tests and callers used the AWS-only row shape:
                # monitor_role_arn, external_id, metadata.
                cloud_provider = "aws"
                monitor_role_arn = acct_row[0]
                external_id = acct_row[1]
                encrypted_secret = None
                metadata = acct_row[2] or {}
                account_id = None
                account_name = None

            if cloud_provider == "aws":
                if not monitor_role_arn or not external_id:
                    raise HTTPException(status_code=400, detail="Missing role ARN/external ID for AWS health check")
                from app.services.aws_connection_tester import AWSConnectionTester
                tester = AWSConnectionTester()
                log_groups = metadata.get("additional_log_group_arns") or []
                s3_buckets = metadata.get("additional_s3_log_bucket_arns") or []
                health = tester.test_log_access(
                    role_arn=monitor_role_arn,
                    external_id=external_id,
                    log_groups=log_groups,
                    s3_buckets=s3_buckets
                )
                db.execute(
                    text("""
                        UPDATE customer_cloud_accounts
                        SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{health}', :health::jsonb, true),
                            updated_at = NOW()
                        WHERE customer_id = :customer_id AND monitor_role_arn = :role_arn
                    """),
                    {"customer_id": customer_id, "role_arn": monitor_role_arn, "health": json.dumps(health)}
                )
            elif provider_has_adapter(str(cloud_provider)):
                if not encrypted_secret:
                    raise HTTPException(status_code=400, detail=f"Missing {cloud_provider} credential reference")
                from sg_core.cloud.onboarding import CloudConnectionValidationError, refresh_cloud_connection_state
                try:
                    token = decrypt_secret(encrypted_secret)
                    connection = refresh_cloud_connection_state(
                        str(cloud_provider),
                        account_id=str(account_id),
                        account_name=account_name or (metadata or {}).get("server_name"),
                        secret=token,
                        metadata=metadata,
                    )
                except CloudConnectionValidationError as exc:
                    raise HTTPException(status_code=400, detail=exc.detail) from exc

                merged_metadata = {
                    **(metadata or {}),
                    **connection.metadata,
                }
                health = connection.health
                db.execute(
                    text("""
                        UPDATE customer_cloud_accounts
                        SET metadata = CAST(:metadata AS jsonb),
                            updated_at = NOW()
                        WHERE customer_id = :customer_id
                          AND cloud_provider = :cloud_provider
                          AND account_id = :account_id
                    """),
                    {
                        "customer_id": customer_id,
                        "cloud_provider": connection.provider,
                        "account_id": account_id,
                        "metadata": json.dumps(merged_metadata),
                    }
                )
            else:
                raise HTTPException(
                    status_code=501,
                    detail=f"Cloud provider '{cloud_provider}' does not support health recheck yet",
                )
            update_sql = None

        if update_sql is not None:
            db.execute(update_sql, {"customer_id": progress_id, "health": json.dumps(health)})
            db.commit()
        return {"success": True, "health": health}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rechecking health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to recheck health: {str(e)}")


@router.post("/load-endpoint-sample")
async def load_endpoint_sample(
    request_data: LoadEndpointSampleRequest,
    customer_id: str = Depends(get_onboarding_customer_id),
):
    """
    Load a small sample endpoint event into OpenSearch to validate ingest and detections.
    """
    if not settings.OPENSEARCH_URL:
        raise HTTPException(status_code=500, detail="OPENSEARCH_URL not configured")

    tenant_id = customer_id
    index = request_data.index or f"sg-{tenant_id}-endpoint-000001"
    pipeline = request_data.pipeline

    sample_doc = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "host": {"hostname": "demo-endpoint", "ip": "10.0.0.5"},
        "event": {
            "category": "process",
            "type": "start",
            "action": "process_start",
            "module": "sentinelguard_agent",
        },
        "process": {
            "name": "powershell.exe",
            "command_line": "powershell.exe -enc base64payload",
            "pid": 4321,
            "parent": {"pid": 1111, "name": "winword.exe"},
        },
        "user": {"name": "demo_user", "domain": "ACME"},
        "rule": {"id": "EDR-SUSPICIOUS-POWERSHELL"},
    }

    bulk_lines = [
        {"index": {"_index": index}},
        sample_doc,
    ]
    ndjson = "\n".join([json.dumps(line) for line in bulk_lines]) + "\n"

    params = {}
    if pipeline:
        params["pipeline"] = pipeline

    try:
        resp = httpx.post(
            settings.OPENSEARCH_URL.rstrip("/") + "/_bulk",
            params=params,
            content=ndjson.encode("utf-8"),
            headers={"Content-Type": "application/x-ndjson"},
            timeout=8.0,
            verify=settings.UPSTREAM_TLS_VERIFY,
        )
        if resp.status_code >= 300:
            logger.error(f"OpenSearch bulk failed: {resp.status_code} {resp.text}")
            raise HTTPException(status_code=502, detail=f"OpenSearch bulk failed: {resp.text}")
        return {"success": True, "index": index, "pipeline": pipeline}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending sample endpoint event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send sample endpoint event: {str(e)}")
