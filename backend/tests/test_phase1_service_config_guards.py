from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[2]
LIBS_ROOT = REPO_ROOT / "backend" / "libs"
if str(LIBS_ROOT) not in sys.path:
    sys.path.insert(0, str(LIBS_ROOT))


def _load_settings_class(relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem.replace(".", "_"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.Settings


def test_ticketing_production_requires_explicit_token_and_tls():
    Settings = _load_settings_class("backend/services/ticketing_service/app/core/config.py")

    with pytest.raises(ValidationError, match="UPSTREAM_TLS_VERIFY"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="ticketing-prod-token",
            UPSTREAM_TLS_VERIFY=False,
        )


def test_ticketing_enrichment_default_targets_canonical_soar_agent(monkeypatch):
    monkeypatch.delenv("AI_ENRICHMENT_AGENT_URL", raising=False)
    monkeypatch.delenv("SOAR_AGENT_URL", raising=False)
    Settings = _load_settings_class("backend/services/ticketing_service/app/core/config.py")

    settings = Settings()

    assert settings.SOAR_AGENT_URL == "http://soar_agent:8000"
    assert settings.AI_ENRICHMENT_AGENT_URL == "http://soar_agent:8000"


def test_detection_defaults_target_canonical_ticketing_and_agent_runtime(monkeypatch):
    monkeypatch.delenv("TICKETING_SERVICE_URL", raising=False)
    monkeypatch.delenv("AGENT_RUNTIME_URL", raising=False)
    Settings = _load_settings_class("backend/services/detection_service/app/core/config.py")

    settings = Settings()

    assert settings.TICKETING_SERVICE_URL == "http://ticketing_service:8000"
    assert settings.AGENT_RUNTIME_URL == "http://agent_runtime:8000"


def test_orchestrator_production_rejects_wildcard_cors():
    Settings = _load_settings_class("backend/services/orchestrator/app/core/config.py")

    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["*"],
            INTERNAL_SERVICE_TOKEN="orchestrator-prod-token",
            UPSTREAM_TLS_VERIFY=True,
        )


def test_agent_siem_production_requires_opensearch_and_upstream_tls():
    Settings = _load_settings_class("backend/agents/siem_agent/app/core/config.py")

    with pytest.raises(ValidationError, match="OPENSEARCH_VERIFY_CERTS"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="siem-prod-token",
            UPSTREAM_TLS_VERIFY=True,
            OPENSEARCH_VERIFY_CERTS=False,
        )


def test_service_siem_production_requires_opensearch_tls_verification():
    Settings = _load_settings_class("backend/agents/siem_agent/app/core/config.py")

    with pytest.raises(ValidationError, match="OPENSEARCH_VERIFY_CERTS"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="siem-service-prod-token",
            UPSTREAM_TLS_VERIFY=True,
            OPENSEARCH_VERIFY_CERTS=False,
        )


def test_wazuh_production_requires_upstream_tls_verification():
    Settings = _load_settings_class("backend/services/wazuh_manager_service/app/core/config.py")

    with pytest.raises(ValidationError, match="UPSTREAM_TLS_VERIFY"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="wazuh-prod-token",
            UPSTREAM_TLS_VERIFY=False,
        )


def test_entitlement_production_requires_keycloak_tls():
    Settings = _load_settings_class("backend/agents/iam_agent/app/core/config.py")

    with pytest.raises(ValidationError, match="KEYCLOAK_VERIFY_TLS"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="iam-prod-token",
            KEYCLOAK_ADMIN_PASSWORD="not-default",
            KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT=True,
            KEYCLOAK_ADMIN_CLIENT_ID="iam-admin-client",
            KEYCLOAK_ADMIN_CLIENT_SECRET="iam-admin-secret",
            KEYCLOAK_VERIFY_TLS=False,
        )


def test_tenant_production_requires_service_account_secret_when_enabled():
    Settings = _load_settings_class("backend/services/tenant_service/app/core/config.py")

    with pytest.raises(ValidationError, match="KEYCLOAK_ADMIN_CLIENT_SECRET"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="tenant-prod-token",
            KEYCLOAK_VERIFY_TLS=True,
            KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT=True,
            KEYCLOAK_ADMIN_CLIENT_SECRET=None,
        )
