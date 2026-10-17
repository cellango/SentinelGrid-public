"""Bounded read-only Keycloak directory observations for role reconciliation."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from urllib.parse import quote, urlsplit
from uuid import UUID
from fastapi import HTTPException
import httpx
from app.core.config import settings, resolve_keycloak_admin_runtime_auth

MAX_USERS = 100
MAX_ROLES = 100


def unavailable():
    raise HTTPException(
        status_code=503, detail="Role directory unavailable or unverified"
    )


@dataclass(frozen=True)
class RoleSnapshot:
    tenant_id: UUID
    user_id: UUID
    roles: tuple[str, ...]
    observed_at: datetime
    directory_realm: str


class RoleDirectoryService:
    def __init__(self, *, transport=None):
        self.transport = transport

    def _realm(self, tenant):
        realm = settings.IAM_ROLE_SYNC_REALMS.get(str(tenant))
        parsed = urlsplit(settings.KEYCLOAK_URL)
        if (
            not realm
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            unavailable()
        return quote(realm, safe="")

    async def _json(self, client, method, url, **kwargs):
        try:
            async with client.stream(method, url, **kwargs) as response:
                if response.status_code != 200:
                    unavailable()
                body = bytearray()
                async for block in response.aiter_bytes():
                    body.extend(block)
                    if len(body) > 1024 * 1024:
                        unavailable()
                return json.loads(body)
        except HTTPException:
            raise
        except Exception:
            unavailable()

    async def _token(self, client):
        try:
            auth = resolve_keycloak_admin_runtime_auth()
        except Exception:
            unavailable()
        if auth.user_realm_name in {".", ".."}:
            unavailable()
        data = await self._json(
            client,
            "POST",
            f"{settings.KEYCLOAK_URL.rstrip('/')}/realms/{quote(auth.user_realm_name, safe='')}/protocol/openid-connect/token",
            data=dict(auth.token_payload),
        )
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("access_token"), str)
            or not data["access_token"]
        ):
            unavailable()
        return {"Authorization": "Bearer " + data["access_token"]}

    def _tenant(self, user):
        try:
            value = user["attributes"]["tenant_id"]
            if (
                not isinstance(value, list)
                or len(value) != 1
                or not isinstance(value[0], str)
            ):
                unavailable()
            return UUID(value[0])
        except (KeyError, TypeError, ValueError):
            unavailable()

    async def _snapshot(self, client, base, headers, tenant, identity):
        user = await self._json(
            client, "GET", f"{base}/users/{identity}", headers=headers
        )
        if (
            not isinstance(user, dict)
            or user.get("id") != str(identity)
            or type(user.get("enabled")) is not bool
        ):
            unavailable()
        if self._tenant(user) != tenant:
            raise HTTPException(status_code=403, detail="Directory tenant mismatch")
        roles = await self._json(
            client,
            "GET",
            f"{base}/users/{identity}/role-mappings/realm/composite",
            headers=headers,
        )
        if not isinstance(roles, list) or len(roles) > MAX_ROLES:
            unavailable()
        names = []
        for role in roles:
            name = role.get("name") if isinstance(role, dict) else None
            if not isinstance(name, str) or not name.strip() or len(name) > 100:
                unavailable()
            names.append(name)
        return RoleSnapshot(
            tenant,
            identity,
            tuple(sorted(set(names))) if user["enabled"] else (),
            datetime.now(timezone.utc),
            settings.IAM_ROLE_SYNC_REALMS[str(tenant)],
        )

    async def observe(self, tenant, identity=None):
        realm = self._realm(tenant)
        base = f"{settings.KEYCLOAK_URL.rstrip('/')}/admin/realms/{realm}"
        async with httpx.AsyncClient(
            transport=self.transport,
            verify=settings.KEYCLOAK_VERIFY_TLS,
            timeout=10.0,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            headers = await self._token(client)
            if identity is not None:
                return [await self._snapshot(client, base, headers, tenant, identity)]
            ids = []
            first = 0
            # Continue to an empty page, even if a server truncates below max.
            while True:
                page = await self._json(
                    client,
                    "GET",
                    f"{base}/users",
                    headers=headers,
                    params={"first": first, "max": 50, "briefRepresentation": "false"},
                )
                if not isinstance(page, list):
                    unavailable()
                if not page:
                    break
                for user in page:
                    try:
                        candidate = UUID(user["id"])
                    except (ValueError, KeyError, TypeError):
                        unavailable()
                    if candidate in ids:
                        unavailable()
                    ids.append(candidate)
                if len(ids) > MAX_USERS:
                    unavailable()
                first += len(page)
            result = []
            for user in ids:
                try:
                    result.append(
                        await self._snapshot(client, base, headers, tenant, user)
                    )
                except HTTPException as error:
                    if error.status_code != 403:
                        raise
                    # Valid foreign-tenant members of a shared realm are excluded;
                    # their tenant is never overwritten by the request tenant.
            return result
