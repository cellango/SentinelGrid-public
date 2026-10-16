"""Focused auth-contract coverage for cert-service internal enrollment auth."""

from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.api import certificates as certificates_api


def test_cert_service_accepts_bearer_service_token(monkeypatch):
    monkeypatch.setattr(certificates_api.settings, "INTERNAL_SERVICE_TOKEN", "shared-token", raising=False)

    assert (
        certificates_api.verify_service_token(
            authorization="Bearer shared-token",
            x_internal_service_token=None,
            x_internal_token=None,
        )
        == "shared-token"
    )


def test_cert_service_accepts_legacy_internal_service_header(monkeypatch):
    monkeypatch.setattr(certificates_api.settings, "INTERNAL_SERVICE_TOKEN", "shared-token", raising=False)

    assert (
        certificates_api.verify_service_token(
            authorization=None,
            x_internal_service_token="shared-token",
            x_internal_token=None,
        )
        == "shared-token"
    )


def test_cert_service_rejects_conflicting_internal_auth_headers(monkeypatch):
    monkeypatch.setattr(certificates_api.settings, "INTERNAL_SERVICE_TOKEN", "shared-token", raising=False)

    with pytest.raises(HTTPException) as excinfo:
        certificates_api.verify_service_token(
            authorization="Bearer shared-token",
            x_internal_service_token="different-token",
            x_internal_token=None,
        )

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Conflicting internal service authentication headers"
