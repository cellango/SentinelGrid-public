import asyncio
import hashlib
import secrets
from types import SimpleNamespace

import pytest

from app.services.backup_code_service import BackupCodeService


class _Response:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("request failed")


class _FakeKC:
    """Minimal async stub for KeycloakAdminClient."""

    def __init__(self, user_data):
        self.user_data = user_data
        self.last_payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def _make_request(self, method, path, json_data=None, params=None):
        if method == "GET":
            return _Response(self.user_data)
        if method == "PUT":
            self.last_payload = json_data
            # Simulate persisted attributes
            if json_data and "attributes" in json_data:
                self.user_data["attributes"] = json_data["attributes"]
            return _Response({})
        return _Response({}, status_code=400)


@pytest.mark.asyncio
async def test_backup_code_generation_and_verify(monkeypatch):
    # Deterministic but unique codes
    code_iter = iter(range(1, 20))
    monkeypatch.setattr(secrets, "token_hex", lambda n=4: f"code{next(code_iter)}")
    monkeypatch.setattr(
        "app.services.backup_code_service.AuditService.log_auth_event",
        lambda **kwargs: None,
    )

    user = {"attributes": {}}
    fake_kc = _FakeKC(user)
    svc = BackupCodeService(keycloak_client=fake_kc)

    codes, hashes = await svc.generate_codes("demo", "user-1", actor_email="u@example.com")

    assert len(codes) == 8
    assert fake_kc.last_payload["attributes"]["backup_codes"] == hashes
    # Hashes should be distinct for unique codes
    assert len(set(hashes)) == len(hashes)

    # Verify consumes one
    ok = await svc.verify_code("demo", "user-1", codes[0], actor_email="u@example.com")
    assert ok is True
    remaining = fake_kc.user_data["attributes"]["backup_codes"]
    assert len(remaining) == 7

    # Double-use should fail
    ok2 = await svc.verify_code("demo", "user-1", codes[0], actor_email="u@example.com")
    assert ok2 is False
