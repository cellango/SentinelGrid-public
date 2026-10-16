"""Focused tenant-isolation coverage for git ingestion routes."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db, get_superadmin_db, get_tenant_session
from app.main import app


@pytest.fixture
def client():
    tenant_db_session = Mock()
    superadmin_db_session = Mock()

    def override_tenant_db():
        yield tenant_db_session

    def override_superadmin_db():
        yield superadmin_db_session

    def unexpected_db():
        raise AssertionError("Unexpected plain DB dependency used")
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = unexpected_db
    app.dependency_overrides[get_tenant_session] = override_tenant_db
    app.dependency_overrides[get_superadmin_db] = override_superadmin_db
    try:
        yield TestClient(app), tenant_db_session, superadmin_db_session
    finally:
        app.dependency_overrides.clear()


def test_ingest_defaults_customer_scope_to_authenticated_tenant(client):
    client, tenant_db_session, _ = client
    tenant_id = str(uuid4())

    with patch("app.api.git_ingestion.GitDataIngestionService") as service_cls:
        service = Mock()
        service.ingest_from_repo.return_value = {"status": "success", "files_processed": 1}
        service_cls.return_value = service

        response = client.post(
            "/internal/llm/git-ingestion/ingest",
            headers={"X-Tenant-ID": tenant_id},
            json={
                "repo_url": "https://github.com/user/repo.git",
                "repo_type": "customer",
                "branch": "main",
            },
        )

    assert response.status_code == 200
    assert service_cls.call_args.kwargs["db_session"] is tenant_db_session
    assert service.ingest_from_repo.call_args.kwargs["tenant_id"] == tenant_id


def test_github_webhook_rejects_cross_tenant_customer_request(client):
    client, _, _ = client
    current_tenant_id = str(uuid4())
    requested_tenant_id = str(uuid4())

    with patch("app.api.git_ingestion.GitDataIngestionService") as service_cls:
        response = client.post(
            f"/internal/llm/git-ingestion/webhook/github?tenant_id={requested_tenant_id}&repo_type=customer",
            headers={"X-Tenant-ID": current_tenant_id, "X-GitHub-Event": "push"},
            json={"repository": {"clone_url": "https://github.com/user/repo.git"}},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"
    service_cls.assert_not_called()


def test_generic_webhook_rejects_cross_tenant_customer_request(client):
    client, _, _ = client
    current_tenant_id = str(uuid4())
    requested_tenant_id = str(uuid4())

    with patch("app.api.git_ingestion.GitDataIngestionService") as service_cls:
        response = client.post(
            "/internal/llm/git-ingestion/webhook/generic",
            headers={"X-Tenant-ID": current_tenant_id},
            json={
                "payload": {"repository": {"clone_url": "https://github.com/user/repo.git"}},
                "repo_type": "customer",
                "tenant_id": requested_tenant_id,
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"
    service_cls.assert_not_called()


def test_list_registered_repos_rejects_cross_tenant_filter(client):
    client, _, _ = client
    current_tenant_id = str(uuid4())
    requested_tenant_id = str(uuid4())

    response = client.get(
        f"/internal/llm/git-ingestion/repos?tenant_id={requested_tenant_id}",
        headers={"X-Tenant-ID": current_tenant_id},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_register_repo_rejects_cross_tenant_filter(client):
    client, _, _ = client
    current_tenant_id = str(uuid4())
    requested_tenant_id = str(uuid4())

    response = client.post(
        "/internal/llm/git-ingestion/repos/register",
        headers={"X-Tenant-ID": current_tenant_id},
        params={
            "repo_url": "https://github.com/user/repo.git",
            "repo_type": "customer",
            "tenant_id": requested_tenant_id,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_poll_all_repos_scopes_to_authenticated_tenant(client):
    client, tenant_db_session, _ = client
    tenant_id = str(uuid4())

    with patch("app.api.git_ingestion.ScheduledIngestionService") as service_cls:
        service = Mock()
        service.poll_all_active_repos.return_value = {"total": 1, "processed": 1, "success": 1, "failed": 0, "skipped": 0}
        service_cls.return_value = service

        response = client.post(
            "/internal/llm/git-ingestion/poll",
            headers={"X-Tenant-ID": tenant_id},
        )

    assert response.status_code == 200
    assert service_cls.call_args.kwargs["db_session"] is tenant_db_session
    assert service.poll_all_active_repos.call_args.kwargs["tenant_id"] == tenant_id


def test_global_ingest_requires_platform_operation_header(client):
    client, _, _ = client
    tenant_id = str(uuid4())

    response = client.post(
        "/internal/llm/git-ingestion/ingest",
        headers={"X-Tenant-ID": tenant_id},
        json={
            "repo_url": "https://github.com/global/repo.git",
            "repo_type": "global",
            "branch": "main",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Global repository operations require X-Platform-Operation: true"


def test_global_register_repo_uses_superadmin_session(client):
    client, _, superadmin_db_session = client
    tenant_id = str(uuid4())

    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    superadmin_db_session.execute.return_value = mock_result

    response = client.post(
        "/internal/llm/git-ingestion/repos/register",
        headers={"X-Tenant-ID": tenant_id, "X-Platform-Operation": "true"},
        params={
            "repo_url": "https://github.com/global/repo.git",
            "repo_type": "global",
            "branch": "main",
        },
    )

    assert response.status_code == 200
    assert response.json()["repo_type"] == "global"
    assert superadmin_db_session.add.called
