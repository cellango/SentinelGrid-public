"""
Organization and tenant provisioning API for IAM Portal.

Decides realm placement (shared/dedicated/auto) based on projected size,
creates organizations, and provisions tenants with Keycloak org/group isolation.
"""

import logging
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.request_context import (
  RequestContext,
  ensure_request_has_any_role,
  get_current_request_context,
  get_superadmin_db,
)
from app.core.config import settings
from app.services.keycloak_admin_factory import build_keycloak_admin
from app.services.multi_tenant_realm_manager import MultiTenantRealmManager
from keycloak import KeycloakAdmin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iam-portal", tags=["iam-portal-orgs"])
SLUG_REGEX = re.compile(r"^[a-z0-9][a-z0-9-]{2,31}$")


# =========================
# Request / Response Models
# =========================


class OrganizationCreate(BaseModel):
  """Create organization request."""
  name: str = Field(..., description="Organization name")
  display_name: Optional[str] = Field(None, description="Display name")
  realm_strategy: Optional[str] = Field("auto", description="shared|dedicated|auto")
  region: Optional[str] = Field("us", description="Region code, default us")
  projected_user_count: Optional[int] = Field(0, description="Projected users to choose strategy")


class TenantCreate(BaseModel):
  """Create tenant under organization."""
  tenant_name: str = Field(..., description="Tenant display name")
  tenant_slug: Optional[str] = Field(None, description="Optional slug; generated if omitted")
  region: Optional[str] = Field("us", description="Region code")


class TenantResponse(BaseModel):
  """Tenant response."""
  id: str
  org_id: str
  realm_name: str
  slug: str
  keycloak_org_id: Optional[str] = None
  keycloak_group_id: Optional[str] = None
  status: str


class OrganizationResponse(BaseModel):
  """Organization response with initial tenant (if created)."""
  id: str
  name: str
  display_name: Optional[str] = None
  realm_strategy: str
  realm_name: str
  region: str
  initial_tenant: Optional[TenantResponse] = None


# =========================
# Helpers
# =========================


def _slugify(value: str) -> str:
  """Generate URL-safe slug."""
  slug = value.lower().strip()
  slug = re.sub(r'[^a-z0-9-]+', '-', slug)
  slug = re.sub(r'-{2,}', '-', slug).strip('-')
  return slug or "org"


def _normalize_slug_candidate(raw_value: str, fallback: str) -> str:
  """
  Normalize a slug candidate:
  - slugify
  - trim to 32 chars
  - ensure minimum length 3 by padding with fallback if needed
  """
  base = _slugify(raw_value or fallback)
  base = base[:32]
  if len(base) < 3:
    base = (f"{base}-{fallback}")[:32]
  return base


def _validate_slug_or_400(slug: str, kind: str = "slug"):
  """Raise HTTP 400 if slug does not meet pattern/length requirements."""
  if not SLUG_REGEX.match(slug):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"Invalid {kind}: must be 3-32 chars, lowercase letters/numbers/hyphens, starting with alphanumeric.",
    )


def _get_realm_manager(db: Session) -> MultiTenantRealmManager:
  """Instantiate MultiTenantRealmManager with Keycloak admin client."""
  admin = build_keycloak_admin(realm_name="master")
  return MultiTenantRealmManager(admin, db)


def _pick_realm(realm_manager: MultiTenantRealmManager, strategy: str, region: str) -> str:
  """Choose or create realm based on strategy."""
  if strategy == "dedicated":
    # Dedicated: create a new shard to isolate org
    return realm_manager._create_new_shard(region)  # pylint: disable=protected-access
  # Shared path
  return realm_manager.get_available_shared_realm(region)


def _resolve_strategy(requested: str, projected_users: int) -> str:
  """Resolve strategy, applying auto threshold."""
  strategy = (requested or "auto").lower()
  if strategy not in ("shared", "dedicated", "auto"):
    strategy = "auto"
  if strategy == "auto":
    threshold = getattr(settings, "REALM_DEDICATED_USER_THRESHOLD", None) or 500
    return "dedicated" if projected_users and projected_users >= threshold else "shared"
  return strategy


def require_platform_admin_request_context(
  request_context: RequestContext = Depends(get_current_request_context),
) -> RequestContext:
  """Require a validated platform-admin identity for provisioning operations."""
  ensure_request_has_any_role(request_context, "PLATFORM_ADMIN")
  return request_context


def _ensure_unique_slug(db: Session, base_slug: str, table: str, column: str = "slug") -> str:
  """Ensure slug uniqueness within a table."""
  attempt = 1
  slug = base_slug

  def _with_suffix(base: str, attempt_num: int) -> str:
    candidate = f"{base}-{attempt_num}"
    # keep total length <= 32 by trimming base if needed
    if len(candidate) > 32:
      trim_len = max(1, 32 - (len(str(attempt_num)) + 1))
      candidate = f"{base[:trim_len]}-{attempt_num}"
    return candidate.strip("-")

  while True:
    result = db.execute(
      text(f"SELECT 1 FROM {table} WHERE {column} = :slug LIMIT 1"),
      {"slug": slug},
    ).first()
    if not result and SLUG_REGEX.match(slug):
      return slug
    slug = _with_suffix(base_slug, attempt)
    attempt += 1


# =========================
# Routes
# =========================


@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
  payload: OrganizationCreate,
  request_context: RequestContext = Depends(require_platform_admin_request_context),
  db: Session = Depends(get_superadmin_db),
):
  """
  Create an organization with realm strategy (shared/dedicated/auto) and provision an initial tenant.
  """
  _ = request_context
  strategy_resolved = _resolve_strategy(payload.realm_strategy or "auto", payload.projected_user_count or 0)
  region = payload.region or "us"

  realm_manager = _get_realm_manager(db)
  realm_name = _pick_realm(realm_manager, strategy_resolved, region)

  # Create customer record (lightweight) to satisfy FK on organizations/tenants
  customer_id = str(uuid.uuid4())
  customer_slug_candidate = _normalize_slug_candidate(payload.name, "customer")
  _validate_slug_or_400(customer_slug_candidate, "customer slug")
  customer_slug = _ensure_unique_slug(db, customer_slug_candidate, "customers")

  db.execute(
    text(
      """
      INSERT INTO customers (id, name, slug, has_dedicated_realm, realm_name, pricing_tier, user_count, org_count, compliance_required, region, status)
      VALUES (:id, :name, :slug, :has_dedicated_realm, :realm_name, :pricing_tier, 0, 0, false, :region, 'active')
      ON CONFLICT (slug) DO NOTHING
      """
    ),
    {
      "id": customer_id,
      "name": payload.name,
      "slug": customer_slug,
      "has_dedicated_realm": strategy_resolved == "dedicated",
      "realm_name": realm_name if strategy_resolved == "dedicated" else None,
      "pricing_tier": "starter",
      "region": region,
    },
  )

  # Create organization row
  org_id = str(uuid.uuid4())
  org_slug_candidate = _normalize_slug_candidate(payload.name, "org")
  _validate_slug_or_400(org_slug_candidate, "organization slug")
  org_slug = _ensure_unique_slug(db, org_slug_candidate, "organizations")
  db.execute(
    text(
      """
      INSERT INTO organizations (id, customer_id, name, slug, realm_name, org_type, status)
      VALUES (:id, :customer_id, :name, :slug, :realm_name, 'business_unit', 'active')
      """
    ),
    {
      "id": org_id,
      "customer_id": customer_id,
      "name": payload.name,
      "slug": org_slug,
      "realm_name": realm_name,
    },
  )

  # Create initial tenant under org
  tenant_resp = await create_tenant_internal(
    db=db,
    realm_manager=realm_manager,
    org_id=org_id,
    customer_id=customer_id,
    tenant_name=f"{payload.name} Main",
    tenant_slug=None,
    region=region,
    realm_name=realm_name,
    strategy=strategy_resolved,
  )

  db.execute(
    text("UPDATE customers SET org_count = org_count + 1 WHERE id = :id"),
    {"id": customer_id},
  )
  db.commit()

  return OrganizationResponse(
    id=org_id,
    name=payload.name,
    display_name=payload.display_name or payload.name,
    realm_strategy=strategy_resolved,
    realm_name=realm_name,
    region=region,
    initial_tenant=tenant_resp,
  )


@router.post("/organizations/{org_id}/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
  org_id: str,
  payload: TenantCreate,
  request_context: RequestContext = Depends(require_platform_admin_request_context),
  db: Session = Depends(get_superadmin_db),
):
  """
  Create an additional tenant under an organization and assign it to the correct realm.
  """
  _ = request_context
  # Fetch org metadata
  org_row = db.execute(
    text(
      """
      SELECT o.id, o.customer_id, o.realm_name
      FROM organizations o
      WHERE o.id = :org_id
      """
    ),
    {"org_id": org_id},
  ).first()

  if not org_row:
    raise HTTPException(status_code=404, detail="Organization not found")

  customer_id = org_row[1]
  org_realm_name = org_row[2]

  realm_manager = _get_realm_manager(db)
  region = payload.region or "us"

  tenant_resp = await create_tenant_internal(
    db=db,
    realm_manager=realm_manager,
    org_id=org_id,
    customer_id=customer_id,
    tenant_name=payload.tenant_name,
    tenant_slug=payload.tenant_slug,
    region=region,
    realm_name=org_realm_name,
    strategy="shared",  # org realm is already chosen; tenants follow org realm
  )

  db.commit()
  return tenant_resp


# =========================
# Internal helpers
# =========================


async def create_tenant_internal(
  db: Session,
  realm_manager: MultiTenantRealmManager,
  org_id: str,
  customer_id: str,
  tenant_name: str,
  tenant_slug: Optional[str],
  region: str,
  realm_name: str,
  strategy: str,
) -> TenantResponse:
  """Create tenant record and provision isolation in Keycloak."""
  slug_candidate = _normalize_slug_candidate(tenant_slug or tenant_name, "tenant")
  _validate_slug_or_400(slug_candidate, "tenant slug")
  slug_base = slug_candidate
  slug = _ensure_unique_slug(db, slug_base, "tenants")

  tenant_id = str(uuid.uuid4())
  db.execute(
    text(
      """
      INSERT INTO tenants (id, name, slug, status, customer_id, organization_id, realm_name, realm_strategy, region)
      VALUES (:id, :name, :slug, 'active', :customer_id, :organization_id, :realm_name, :realm_strategy, :region)
      """
    ),
    {
      "id": tenant_id,
      "name": tenant_name,
      "slug": slug,
      "customer_id": customer_id,
      "organization_id": org_id,
      "realm_name": realm_name,
      "realm_strategy": strategy,
      "region": region,
    },
  )

  # Assign org/group isolation in Keycloak
  kc_refs = realm_manager.assign_tenant_to_shared_realm(
    tenant_id=tenant_id,
    tenant_slug=slug,
    realm_name=realm_name,
    customer_id=customer_id,
  )

  db.execute(
    text(
      """
      UPDATE tenants
      SET keycloak_org_id = :org_id, keycloak_group_id = :group_id
      WHERE id = :tenant_id
      """
    ),
    {
      "org_id": kc_refs.get("keycloak_org_id"),
      "group_id": kc_refs.get("keycloak_group_id"),
      "tenant_id": tenant_id,
    },
  )

  return TenantResponse(
    id=tenant_id,
    org_id=org_id,
    realm_name=realm_name,
    slug=slug,
    keycloak_org_id=kc_refs.get("keycloak_org_id"),
    keycloak_group_id=kc_refs.get("keycloak_group_id"),
    status="active",
  )
