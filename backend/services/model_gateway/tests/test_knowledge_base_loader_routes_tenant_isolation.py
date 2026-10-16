"""Tenant-isolation coverage for knowledge-base loader routes."""

from uuid import uuid4
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db, get_superadmin_db, get_tenant_session
from app.main import app as fastapi_app


def _unexpected_dependency():
    raise AssertionError("Unexpected database dependency used")
    yield  # pragma: no cover


def test_load_nist_uses_superadmin_db_without_tenant_header(db_session):
    def _get_superadmin_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _unexpected_dependency
    fastapi_app.dependency_overrides[get_tenant_session] = _unexpected_dependency
    fastapi_app.dependency_overrides[get_superadmin_db] = _get_superadmin_db
    try:
        client = TestClient(fastapi_app)
        with patch("app.api.knowledge_base_loader.KnowledgeBaseLoader") as loader_cls:
            loader = MagicMock()
            loader.load_nist_controls.return_value = {"framework": "NIST 800-53", "loaded": 1, "errors": 0}
            loader_cls.return_value = loader

            response = client.post("/internal/llm/knowledge-base/load/nist")
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["framework"] == "NIST 800-53"

def test_load_soc2_uses_superadmin_db_dependency(db_session):
    def _get_superadmin_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _unexpected_dependency
    fastapi_app.dependency_overrides[get_tenant_session] = _unexpected_dependency
    fastapi_app.dependency_overrides[get_superadmin_db] = _get_superadmin_db
    try:
        client = TestClient(fastapi_app)
        with patch("app.api.knowledge_base_loader.KnowledgeBaseLoader") as loader_cls:
            loader = MagicMock()
            loader.load_soc2_content.return_value = {"framework": "SOC 2", "loaded": 1, "errors": 0}
            loader_cls.return_value = loader

            response = client.post("/internal/llm/knowledge-base/load/soc2")
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["framework"] == "SOC 2"
    loader.load_soc2_content.assert_called_once_with(None)


def test_load_knowledge_bases_uses_superadmin_db_and_loads(db_session):
    def _get_superadmin_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _unexpected_dependency
    fastapi_app.dependency_overrides[get_tenant_session] = _unexpected_dependency
    fastapi_app.dependency_overrides[get_superadmin_db] = _get_superadmin_db
    try:
        client = TestClient(fastapi_app)
        with patch("app.api.knowledge_base_loader.KnowledgeBaseLoader") as loader_cls:
            loader = MagicMock()
            loader.load_nist_controls.return_value = {"loaded": 2, "errors": 0}
            loader.load_soc2_content.return_value = {"loaded": 1, "errors": 0}
            loader_cls.return_value = loader

            response = client.post(
                "/internal/llm/knowledge-base/load",
                json={"frameworks": ["nist", "soc2"]},
            )
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["summary"] == {"total_loaded": 3, "total_errors": 0}
    loader.load_nist_controls.assert_called_once_with(None)
    loader.load_soc2_content.assert_called_once_with(None)


def test_soc2_health_uses_tenant_session_and_rejects_mismatch(db_session):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())

    def _get_tenant_session():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _unexpected_dependency
    fastapi_app.dependency_overrides[get_tenant_session] = _get_tenant_session
    try:
        client = TestClient(fastapi_app)
        response = client.get(
            "/internal/llm/knowledge-base/health/soc2",
            headers={"X-Tenant-ID": tenant_a},
            params={"tenant_id": tenant_b},
        )
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_load_report_uses_tenant_session_and_scopes_by_header(db_session):
    tenant_id = str(uuid4())

    def _get_tenant_session():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _unexpected_dependency
    fastapi_app.dependency_overrides[get_tenant_session] = _get_tenant_session
    try:
        client = TestClient(fastapi_app)
        with patch("app.api.knowledge_base_loader.KnowledgeBaseLoader") as loader_cls:
            loader = MagicMock()
            loader.load_report_content.return_value = {"status": "success", "loaded": 3}
            loader_cls.return_value = loader

            response = client.post(
                "/internal/llm/knowledge-base/load/report",
                headers={"X-Tenant-ID": tenant_id},
                json={
                    "tenant_id": tenant_id,
                    "report_id": "report-123",
                    "sections": [{"title": "Summary", "content": "ok"}],
                },
            )
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    loader.load_report_content.assert_called_once()
    assert loader.load_report_content.call_args.kwargs["tenant_id"] == tenant_id


def test_load_report_rejects_cross_tenant_request(db_session):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())

    def _get_tenant_session():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _unexpected_dependency
    fastapi_app.dependency_overrides[get_tenant_session] = _get_tenant_session
    try:
        client = TestClient(fastapi_app)
        response = client.post(
            "/internal/llm/knowledge-base/load/report",
            headers={"X-Tenant-ID": tenant_a},
            json={
                "tenant_id": tenant_b,
                "report_id": "report-123",
                "sections": [],
            },
        )
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"
