import pytest

from app.services.adaptive_auth import AdaptiveAuthService


def test_adaptive_auth_risk_and_requirements_high_risk():
    svc = AdaptiveAuthService()
    ctx = {
        "device_trusted": False,
        "new_device": True,
        "device_posture": "noncompliant",
        "ip_reputation": "high",
        "impossible_travel": True,
        "recent_failed_logins": 3,
    }

    reqs = svc.determine_auth_requirements(user_id="u1", auth_context=ctx, tenant_id=None)
    assert reqs["risk_level"] in {"high", "critical"}
    assert "totp" in reqs["required_factors"]
    assert reqs["policies"].get("allow_backup_codes") is True


@pytest.mark.asyncio
async def test_adaptive_auth_backup_code_path(monkeypatch):
    svc = AdaptiveAuthService()

    class _FakeBackup:
        def __init__(self, valid=True):
            self.valid = valid

        async def verify_code(self, realm, user_id, code, actor_email=None):
            return self.valid

    # Force backup code to satisfy TOTP requirement
    ctx = {
        "realm": "demo",
        "email": "user@demo.sentinelgrid.ai",
        "ip_reputation": "high",
        "new_device": True,
        "impossible_travel": True,
        "device_posture": "noncompliant",
        "recent_failed_logins": 2,
    }
    svc_backup_service = _FakeBackup(valid=True)

    provided_factors = [
        {"type": "backup_code", "data": {"code": "1234"}},
    ]

    # Monkeypatch to bypass real backup service creation
    monkeypatch.setattr("app.services.adaptive_auth.BackupCodeService", lambda: svc_backup_service)

    result = await svc.verify_adaptive_auth(
        user_id="u1",
        provided_factors=provided_factors,
        auth_context=ctx,
        tenant_id=None,
    )

    assert result["verified"] is True
    assert any(fr["type"] == "backup_code" and fr["verified"] for fr in result["factor_results"])
