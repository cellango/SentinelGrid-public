"""Fail-closed UUID ownership and transaction-coupled audit unit regressions."""
import asyncio
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

with patch("sqlalchemy.engine.Engine.connect", side_effect=RuntimeError("No database in unit tests")):
    from app.core.tenant_isolation import TenantIsolationValidator as Validator
    from app.services.audit_logger import AuditLogger


@pytest.mark.parametrize("value", [None, "", "tenant-slug", "not-a-uuid", 123])
def test_tenant_requires_uuid(value):
    with pytest.raises((HTTPException, ValueError)):
        Validator.validate_tenant_id(value)


def test_resource_requires_verified_tenant_not_just_user_id():
    with pytest.raises(HTTPException):
        Validator.validate_resource_ownership(uuid4(), uuid4())


def test_resource_ownership_compares_verified_tenant():
    with pytest.raises(HTTPException):
        Validator.validate_resource_ownership(uuid4(), uuid4(), authenticated_tenant_id=uuid4())


def test_resource_ownership_accepts_same_uuid_in_different_spelling():
    tenant = uuid4()
    Validator.validate_resource_ownership(str(tenant).upper(), uuid4(), authenticated_tenant_id=tenant)


def test_query_rejects_foreign_tenant():
    with pytest.raises(HTTPException):
        Validator.get_tenant_id_for_query(uuid4(), uuid4(), authenticated_tenant_id=uuid4())


def test_query_defaults_only_to_verified_tenant():
    tenant = uuid4()
    assert Validator.get_tenant_id_for_query(None, uuid4(), authenticated_tenant_id=tenant) == tenant


def test_missing_tenants_never_compare_equal():
    with pytest.raises(HTTPException):
        Validator.enforce_tenant_isolation(None, None)


def test_audit_event_is_staged_in_callers_transaction():
    db = Mock()
    AuditLogger(db).log_entitlement_event("created", uuid4(), uuid4(), uuid4())
    db.add.assert_called_once()
    db.flush.assert_called_once()
    db.commit.assert_not_called()


def test_audit_storage_error_propagates_to_caller():
    db = Mock()
    db.flush.side_effect = RuntimeError("synthetic audit outage")
    with pytest.raises(RuntimeError, match="synthetic audit outage"):
        AuditLogger(db).log_entitlement_event("created", uuid4(), uuid4(), uuid4())


def test_audit_redacts_credentials_and_copies_payload():
    db = Mock()
    payload = {"access_token": "synthetic-sensitive", "nested": {"password": "synthetic-sensitive"}, "status": "active"}
    AuditLogger(db).log_entitlement_event("created", uuid4(), uuid4(), uuid4(), metadata=payload)
    row = db.add.call_args.args[0]
    assert "synthetic-sensitive" not in str(row.metadata_json)
    assert row.metadata_json["status"] == "active"
    assert payload["access_token"] == "synthetic-sensitive"


def test_audit_refuses_an_unidentified_user_actor():
    with pytest.raises(ValueError):
        AuditLogger(Mock()).log_entitlement_event("created", uuid4(), uuid4(), None)


def test_missing_access_grant_configuration_returns_unavailable(monkeypatch):
    from app.core import database
    from app.api import request_context
    monkeypatch.setattr(database, "_IAMSessionLocal", None)
    dependency = request_context.get_entitlement_session(request_context.RequestContext(uuid4(), str(uuid4())))
    with pytest.raises(HTTPException) as result:
        next(dependency)
    assert result.value.status_code == 503


def test_invalid_tenant_never_opens_a_session():
    from sg_core.tenant_session import tenant_session
    factory = Mock()
    with pytest.raises(ValueError):
        with tenant_session(factory, "tenant-slug"):
            pass
    factory.assert_not_called()


@pytest.mark.parametrize("target", ["sqlite:///synthetic", "postgresql://other:synthetic@db.example.test/catalog"])
def test_grant_store_rejects_non_postgres_or_shared_target(monkeypatch,target):
    from sqlalchemy.engine import make_url
    from app.core import database
    monkeypatch.setattr(database.settings,"IAM_DB_URL",target)
    monkeypatch.setattr(database,"engine",Mock(url=make_url("postgresql://review:synthetic@db.example.test/catalog")))
    creator=Mock()
    monkeypatch.setattr(database,"create_engine",creator)
    with pytest.raises(ValueError):database._iam_engine()
    creator.assert_not_called()


@pytest.mark.parametrize("path", ["", "/batch"])
def test_http_cannot_claim_completed_decision_without_durable_audit(monkeypatch, path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import AsyncMock
    from app.api import authorize, request_context
    from app.services.evaluation_engine import EvaluationResult
    tenant, user = uuid4(), uuid4()
    app = FastAPI()
    app.include_router(authorize.router)
    app.dependency_overrides[request_context.get_current_request_context] = lambda: request_context.RequestContext(tenant, str(user))
    app.dependency_overrides[request_context.get_tenant_session] = lambda: Mock()
    app.dependency_overrides[request_context.get_entitlement_session] = lambda: Mock()
    engine = Mock()
    engine.evaluate = AsyncMock(return_value=EvaluationResult("deny", "Audit unavailable"))
    engine.evaluate_batch = AsyncMock(return_value=[EvaluationResult("deny", "Audit unavailable")])
    monkeypatch.setattr(authorize, "EvaluationEngine", Mock(return_value=engine))
    body = dict(tenant_id=str(tenant), user_id=str(user), resource_type="document", resource_id="synthetic", action="read")
    response = TestClient(app).post("/api/v1/authorize" + path, json={"requests": [body]} if path else body)
    assert response.status_code == 503


def test_catalog_store_respects_validated_settings_url(monkeypatch):
    from sqlalchemy.engine import make_url
    from app.core import database
    configured = make_url("postgresql://review@catalog.example.test/catalog")
    monkeypatch.setattr(database.settings, "DB_URL", str(configured))
    monkeypatch.setattr(database, "shared_engine", Mock(url=make_url("postgresql://review@environment.example.test/catalog")))
    created = Mock()
    creator = Mock(return_value=created)
    reset = Mock()
    monkeypatch.setattr(database, "create_engine", creator)
    monkeypatch.setattr(database, "install_tenant_pool_reset", reset)
    assert database._catalog_engine() is created
    assert creator.call_args.args[0] == configured
    reset.assert_called_once_with(created)
