"""
App assignments API.
Assign/unassign entitlements (client roles) to groups/users for an application.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.app_catalog import get_token_data, get_realm_for_tenant
from app.services.keycloak_admin_client import KeycloakAdminClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/iam-portal/apps", tags=["app-assignments"])


class AssignmentOut(BaseModel):
    id: str
    subject_type: str  # group|user
    subject_id: str
    subject_name: str | None = None
    entitlement_id: str
    entitlement_name: str | None = None


class AssignmentIn(BaseModel):
    subject_type: str  # group|user
    subject_id: str
    entitlement_id: str


async def _kc_lookup_group(kc: KeycloakAdminClient, realm: str, name: str):
    resp = await kc._make_request("GET", f"/realms/{realm}/groups", params={"search": name})
    resp.raise_for_status()
    groups = resp.json() or []
    return next((g for g in groups if g.get("name") == name), None)


async def _kc_lookup_user(kc: KeycloakAdminClient, realm: str, token: str):
    resp = await kc._make_request("GET", f"/realms/{realm}/users", params={"search": token})
    resp.raise_for_status()
    users = resp.json() or []
    return next((u for u in users if u.get("username") == token or u.get("email") == token), None)


async def _kc_client_roles(kc: KeycloakAdminClient, realm: str, client_id: str):
    roles_resp = await kc._make_request("GET", f"/realms/{realm}/clients/{client_id}/roles")
    roles_resp.raise_for_status()
    return {r["name"]: r for r in roles_resp.json() if "name" in r}


@router.get("/{app_id}/assignments", response_model=List[AssignmentOut])
async def list_assignments(
    app_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)

    try:
        async with KeycloakAdminClient() as kc:
            # Fetch client roles
            roles = await _kc_client_roles(kc, realm, app_id)

            assignments: list[AssignmentOut] = []

            # group role mappings
            grp_resp = await kc._make_request("GET", f"/realms/{realm}/groups")
            grp_resp.raise_for_status()
            for g in grp_resp.json() or []:
                g_roles_resp = await kc._make_request(
                    "GET", f"/realms/{realm}/groups/{g['id']}/role-mappings/clients/{app_id}"
                )
                if g_roles_resp.status_code >= 300:
                    continue
                for r in g_roles_resp.json() or []:
                    assignments.append(
                        AssignmentOut(
                            id=f"group-{g['id']}-{r['id']}",
                            subject_type="group",
                            subject_id=g["id"],
                            subject_name=g.get("name"),
                            entitlement_id=r.get("name") or r.get("id"),
                            entitlement_name=r.get("name"),
                        )
                    )

            # user role mappings (limited to first page)
            user_resp = await kc._make_request("GET", f"/realms/{realm}/users", params={"max": 50})
            user_resp.raise_for_status()
            for u in user_resp.json() or []:
                u_roles_resp = await kc._make_request(
                    "GET", f"/realms/{realm}/users/{u['id']}/role-mappings/clients/{app_id}"
                )
                if u_roles_resp.status_code >= 300:
                    continue
                for r in u_roles_resp.json() or []:
                    assignments.append(
                        AssignmentOut(
                            id=f"user-{u['id']}-{r['id']}",
                            subject_type="user",
                            subject_id=u["id"],
                            subject_name=u.get("username") or u.get("email"),
                            entitlement_id=r.get("name") or r.get("id"),
                            entitlement_name=r.get("name"),
                        )
                    )

            return assignments
    except Exception as e:
        logger.error(f"Failed to list assignments for app {app_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list assignments")


@router.post("/{app_id}/assignments")
async def add_assignment(
    app_id: str,
    body: AssignmentIn,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)

    try:
        async with KeycloakAdminClient() as kc:
            roles = await _kc_client_roles(kc, realm, app_id)
            role = roles.get(body.entitlement_id) or next((r for r in roles.values() if r.get("id") == body.entitlement_id), None)
            if not role:
                raise HTTPException(status_code=400, detail="Entitlement not found on client")

            if body.subject_type == "group":
                target_group = await _kc_lookup_group(kc, realm, body.subject_id)
                if not target_group:
                    raise HTTPException(status_code=404, detail="Group not found")
                await kc._make_request(
                    "POST",
                    f"/realms/{realm}/groups/{target_group['id']}/role-mappings/clients/{app_id}",
                    json_data=[role],
                )
            else:
                target_user = await _kc_lookup_user(kc, realm, body.subject_id)
                if not target_user:
                    raise HTTPException(status_code=404, detail="User not found")
                await kc._make_request(
                    "POST",
                    f"/realms/{realm}/users/{target_user['id']}/role-mappings/clients/{app_id}",
                    json_data=[role],
                )
            return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add assignment for app {app_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add assignment")


@router.delete("/{app_id}/assignments/{assignment_id}")
async def remove_assignment(
    app_id: str,
    assignment_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)

    try:
        subject_type, subject_id, role_id = assignment_id.split("-", 2)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid assignment id format")

    try:
        async with KeycloakAdminClient() as kc:
            if subject_type == "group":
                target_group = await _kc_lookup_group(kc, realm, subject_id)
                if not target_group:
                    raise HTTPException(status_code=404, detail="Group not found")
                await kc._make_request(
                    "DELETE",
                    f"/realms/{realm}/groups/{target_group['id']}/role-mappings/clients/{app_id}",
                    json_data=[{"id": role_id}],
                )
            else:
                target_user = await _kc_lookup_user(kc, realm, subject_id)
                if not target_user:
                    raise HTTPException(status_code=404, detail="User not found")
                await kc._make_request(
                    "DELETE",
                    f"/realms/{realm}/users/{target_user['id']}/role-mappings/clients/{app_id}",
                    json_data=[{"id": role_id}],
                )
            return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove assignment for app {app_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove assignment")
